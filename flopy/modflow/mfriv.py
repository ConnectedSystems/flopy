"""
mfriv module.  Contains the ModflowRiv class. Note that the user can access
the ModflowRiv class as `flopy.modflow.ModflowRiv`.

Additional information for this MODFLOW package can be found at the `Online
MODFLOW Guide
<http://water.usgs.gov/ogw/modflow/MODFLOW-2005-Guide/index.html?riv.htm>`_.

"""
import sys
import numpy as np
from ..pakbase import Package
from flopy.utils.util_list import MfList
from flopy.utils import check


class ModflowRiv(Package):
    """
    MODFLOW River Package Class.

    Parameters
    ----------
    model : model object
        The model object (of type :class:`flopy.modflow.mf.Modflow`) to which
        this package will be added.
    ipakcb : int
        A flag that is used to determine if cell-by-cell budget data should be
        saved. If ipakcb is non-zero cell-by-cell budget data will be saved.
        (default is 0).
    stress_period_data : list of boundaries, or recarray of boundaries, or
        dictionary of boundaries.
        Each river cell is defined through definition of
        layer (int), row (int), column (int), stage (float), cond (float),
        rbot (float).
        The simplest form is a dictionary with a lists of boundaries for each
        stress period, where each list of boundaries itself is a list of
        boundaries. Indices of the dictionary are the numbers of the stress
        period. This gives the form of::

            stress_period_data =
            {0: [
                [lay, row, col, stage, cond, rbot],
                [lay, row, col, stage, cond, rbot],
                [lay, row, col, stage, cond, rbot]
                ],
            1:  [
                [lay, row, col, stage, cond, rbot],
                [lay, row, col, stage, cond, rbot],
                [lay, row, col, stage, cond, rbot]
                ], ...
            kper:
                [
                [lay, row, col, stage, cond, rbot],
                [lay, row, col, stage, cond, rbot],
                [lay, row, col, stage, cond, rbot]
                ]
            }

        Note that if the number of lists is smaller than the number of stress
        periods, then the last list of rivers will apply until the end of the
        simulation. Full details of all options to specify stress_period_data
        can be found in the flopy3 boundaries Notebook in the basic
        subdirectory of the examples directory.
    dtype : custom datatype of stress_period_data.
        (default is None)
        If None the default river datatype will be applied.
    naux : int
        number of auxiliary variables
    extension : string
        Filename extension (default is 'riv')
    unitnumber : int
        File unit number (default is 18).
    options : list of strings
        Package options. (default is None).        

    Attributes
    ----------
    mxactr : int
        Maximum number of river cells for a stress period.  This is calculated
        automatically by FloPy based on the information in
        layer_row_column_data.

    Methods
    -------

    See Also
    --------

    Notes
    -----
    Parameters are not supported in FloPy.

    Examples
    --------

    >>> import flopy
    >>> m = flopy.modflow.Modflow()
    >>> lrcd = {}
    >>> lrcd[0] = [[2, 3, 4, 15.6, 1050., -4]]  #this river boundary will be
    >>>                                         #applied to all stress periods
    >>> riv = flopy.modflow.ModflowRiv(m, stress_period_data=lrcd)

    """

    def __init__(self, model, ipakcb=0, stress_period_data=None, dtype=None,
                 extension='riv', unitnumber=18, options=None, **kwargs):
        """
        Package constructor.

        """
        # Call parent init to set self.parent, extension, name and unit number
        Package.__init__(self, model, extension, 'RIV', unitnumber)
        self.heading = '# RIV for MODFLOW, generated by Flopy.'
        self.url = 'riv.htm'
        if ipakcb != 0:
            self.ipakcb = 53
        else:
            self.ipakcb = 0  # 0: no cell by cell terms are written
        self.mxactr = 0
        self.np = 0
        if options is None:
            options = []
        self.options = options
        if dtype is not None:
            self.dtype = dtype
        else:
            self.dtype = self.get_default_dtype(structured=self.parent.structured)
        # self.stress_period_data = MfList(model, self.dtype, stress_period_data)
        self.stress_period_data = MfList(self, stress_period_data)
        self.parent.add_package(self)

    def check(self, f=None, verbose=True, level=1):
        """
        Check package data for common errors.

        Parameters
        ----------
        f : str or file handle
            String defining file name or file handle for summary file
            of check method output. If a string is passed a file handle
            is created. If f is None, check method does not write
            results to a summary file. (default is None)
        verbose : bool
            Boolean flag used to determine if check method results are
            written to the screen.
        level : int
            Check method analysis level. If level=0, summary checks are
            performed. If level=1, full checks are performed.

        Returns
        -------
        None

        Examples
        --------

        >>> import flopy
        >>> m = flopy.modflow.Modflow.load('model.nam')
        >>> m.riv.check()

        """
        basechk = super(ModflowRiv, self).check(verbose=False)
        chk = check(self, f=f, verbose=verbose, level=level)
        chk.summary_array = basechk.summary_array

        for per in self.stress_period_data.data.keys():
            if isinstance(self.stress_period_data.data[per], np.recarray):
                spd = self.stress_period_data.data[per]
                inds = (spd.k, spd.i, spd.j) if self.parent.structured else (spd.node)

                # check that river stage and bottom are above model cell bottoms
                # also checks for nan values
                botms = self.parent.dis.botm.array[inds]

                for elev in ['stage', 'rbot']:
                    chk.stress_period_data_values(spd, spd[elev] < botms,
                                                  col=elev,
                                                  error_name='{} below cell bottom'.format(elev),
                                                  error_type='Error')

                # check that river stage is above the rbot
                chk.stress_period_data_values(spd, spd['rbot'] > spd['stage'],
                                              col='stage',
                                              error_name='RIV stage below rbots',
                                              error_type='Error')
        chk.summarize()
        return chk


    @staticmethod
    def get_empty(ncells=0, aux_names=None, structured=True):
        # get an empty recarray that correponds to dtype
        dtype = ModflowRiv.get_default_dtype(structured=structured)
        if aux_names is not None:
            dtype = Package.add_to_dtype(dtype, aux_names, np.float32)
        d = np.zeros((ncells, len(dtype)), dtype=dtype)
        d[:, :] = -1.0E+10
        return np.core.records.fromarrays(d.transpose(), dtype=dtype)

    @staticmethod
    def get_default_dtype(structured=True):
        if structured:
            dtype = np.dtype([("k", np.int), ("i", np.int),
                              ("j", np.int), ("stage", np.float32),
                              ("cond", np.float32), ("rbot", np.float32)])
        else:
            dtype = np.dtype([("node", np.int), ("stage", np.float32),
                              ("cond", np.float32), ("rbot", np.float32)])

        return dtype

    def ncells(self):
        # Return the  maximum number of cells that have river
        # (developed for MT3DMS SSM package)
        return self.stress_period_data.mxact

    def write_file(self, check=True):
        """
        Write the package file.

        Parameters
        ----------
        check : boolean
            Check package data for common errors. (default True)

        Returns
        -------
        None

        """
        if check: # allows turning off package checks when writing files at model level
            self.check(f='{}.chk'.format(self.name[0]), verbose=self.parent.verbose, level=1)
        f_riv = open(self.fn_path, 'w')
        f_riv.write('{0}\n'.format(self.heading))
        line = '{0:10d}{1:10d}'.format(self.stress_period_data.mxact, self.ipakcb)
        for opt in self.options:
            line += ' ' + str(opt)
        line += '\n'
        f_riv.write(line)
        self.stress_period_data.write_transient(f_riv)
        f_riv.close()

    def add_record(self, kper, index, values):
        try:
            self.stress_period_data.add_record(kper, index, values)
        except Exception as e:
            raise Exception("mfriv error adding record to list: " + str(e))

    @staticmethod
    def load(f, model, nper=None, ext_unit_dict=None, check=True):
        """
        Load an existing package.

        Parameters
        ----------
        f : filename or file handle
            File to load.
        model : model object
            The model object (of type :class:`flopy.modflow.mf.Modflow`) to
            which this package will be added.
        nper : int
            The number of stress periods.  If nper is None, then nper will be
            obtained from the model object. (default is None).
        ext_unit_dict : dictionary, optional
            If the arrays in the file are specified using EXTERNAL,
            or older style array control records, then `f` should be a file
            handle.  In this case ext_unit_dict is required, which can be
            constructed using the function
            :class:`flopy.utils.mfreadnam.parsenamefile`.
        check : boolean
            Check package data for common errors. (default True)

        Returns
        -------
        rch : ModflowRiv object
            ModflowRiv object.

        Examples
        --------

        >>> import flopy
        >>> m = flopy.modflow.Modflow()
        >>> riv = flopy.modflow.ModflowRiv.load('test.riv', m)

        """

        if model.verbose:
            sys.stdout.write('loading riv package file...\n')

        return Package.load(model, ModflowRiv, f, nper, check=check)
