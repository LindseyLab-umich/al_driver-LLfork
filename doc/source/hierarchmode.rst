.. _page-hierarch:

***************************************
Hierarchical Fitting Mode
***************************************


.. figure:: hierarchy.pdf
  :width: 500
  :align: center
  
  **Fig. 1:** The ChIMES parameter hierarchy for a Si, O, H, and N-containing system.


The most common strategy for generating machine-learned interatomic models involves fitting all parameters at once but this can (1) prove challenging for high complexity problems and (2) limit transferability. However, the inhently hierarchical nature of ChIMES parameters allows for an alternative strategy in which relatively low-complexity "families" of parameters can be generated independently from one another. These families can then be combined and built upon via transfer learning to describe higher complexity systems. For example, Fig. 1 shows the CHIMES parameter hierarchy for an up-to-4-body model describing interactions in a Si, O, H, and N-containing system. Each "tile" represents a family of parametrs, e.g., the H tile contains the 1-through 4-body parameters for H, H-H, H-H-H, and H-H-H-H interactions. Tiles on the same row (e.g. H and N) can be fit indepent of one another; tiles containing two or more atoms describe *only* simultaneous cross iteractions between the indicated atom types, e.g., the HN tile *only* contains parameters for HN, HHN, HNN, HHHN, HHNN, and HNNN interactions. Practically, this means simulating an H- and N- containing system requires all the parameters contained in the H, N, and HN tiles. 

Fitting row-1 tiles requires no special treatment. However, fitting tiles on row-2 and above requires pre-processing training data during each learning iteration to remove contributions from the relavant lower row tiles. For example, an HN tile fit would require H and N tile contributions to be removed from the training data. Additionally, parameter sets must be combined into a cohesive file before running dynamics. *The ALD can perform these tasks automatically.*

This section provides an overview of how to configure the ALD for a hierarchical fitting strategy, within the context of a liquid C/N system. Before proceding, ensure you have read through and fully understand the :ref:`page-basic`.


For additional information on strategies and benefits of hierarchical fitting, see: 

* R.K. Lindsey, B. Steele, S. Bastea, I.-F. Kuo, L.E. Fried, and N. Goldman *In Prep*

.. **UPDATE JOURNAL** ... this would be for C/N ... try for JCTC   `(link) < UPDATE >`_

-------

============================
Example Fit: Solid C/N
============================


.. Note ::

    Files for this example are located in ``./<al_driver base folder>/examples/hierarch_fit``
    
In this section, an example 3-iteration fit for a solid C- and N-containing system at ~75% C, 6000K, and 3.5 g/cc is overviewed **<DOUBLE CHECK THESE NUMBERS>**. The model will include up-to-4 body interactions. Given the substantial increase in number of fitting parameters and system complexity relative to pure carbon case the basic fitting example, this case will take substantially longer to run.


The neccesary input files and directory tree structure are provided in the example folder, i.e.:

.. code-block :: 
    :emphasize-lines: 4,14-16

    $: tree 
    .
    ├── ALC-0_BASEFILES
    │   |-- 20.3percN_3.5gcc.temps
    │   |-- 20.3percN_3.5gcc.xyzf
    │   |-- fm_setup.in
    │   └── traj_list.dat
    ├── CHIMESMD_BASEFILES
    │   |-- base.run_md.in
    │   |-- bonds.dat
    │   |-- case-0.indep-0.input.xyz
    │   |-- case-0.indep-0.run_md.in
    │   └── run_molanal.sh
    ├── HIERARCH_PARAMS
    │   |-- C.params.txt.reduced
    │   └── N.params.txt.reduced
    └── QM_BASEFILES
        |-- 6000.INCAR
        |-- C.POTCAR
        |-- KPOINTS
        |-- N.POTCAR
        └── POTCAR
    
Comparing with the ``ALC-0_BASEFILES`` folder provided in the :ref:`page-basic`, the primary difference is the ``HIERARCH_PARAMS`` directory, i.e., which contains parameters for the C and N tiles, and the ``.temps`` file, which provides a single temperature for each frame in the corresponding ``.xyzf`` file, are highlighted.


-------

------------------------------------------
Input Files 
------------------------------------------

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The ALC-0_BASEFILES Files 
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. Warning ::

    The ``ALC-0_BASEFILES/fm_setup.in`` requires a few special edits for hierarchical learning mode:

    * ``fm_setup.in`` should have ``# HIERARC #`` set ``true``
    * All 1- through *n*\-body interactions described in in the reference (``HIERARCH_PARAM_FILES``) files must be explicitly excluded
    * Orders in the ``ALC-0_BASEFILES/fm_setup.in`` file should be greater or equal to those in the reference (``HIERARCH_PARAM_FILES``) files
    * ``TYPEIDX`` and ``PAIRIDX`` entries in the base fm_setup.in file must be consistent with respect to the ``HIERARCH_PARAM_FILES`` files
    * ``SPECIAL XB`` cutoffs must be set to ``SPECIFIC N``, where *N* is the number of **NON**-excluded *X*\B interaction types 
    
    For additional information on how to configure these options, see the ChIMES LSQ manual `(link <UPDATE LINK>)`_.



~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The config.py File
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The `config.py` file is given below:

.. code-block :: python
    :linenos:
    :emphasize-lines: 55-57
    
    ################################
    ##### General variables
    ################################

    EMAIL_ADD     = "lindsey11@llnl.gov" # driver will send updates on the status of the current run ... If blank (""), no emails are sent

    ATOM_TYPES = ['C', 'N']
    NO_CASES = 1

    DRIVER_DIR     = "/p/lustre2/rlindsey/al_driver/src/"
    WORKING_DIR    = "/p/lustre2/rlindsey/al_driver/examples/hierarch_fit"
    CHIMES_SRCDIR  = "/p/lustre2/rlindsey/chimes_lsq/src/"

    ################################
    ##### ChIMES LSQ
    ################################

    ALC0_FILES    = WORKING_DIR + "ALL_BASE_FILES/ALC-0_BASEFILES/"
    CHIMES_LSQ    = CHIMES_SRCDIR + "../build/chimes_lsq"
    CHIMES_SOLVER = CHIMES_SRCDIR + "../build/chimes_lsq.py"
    CHIMES_POSTPRC= CHIMES_SRCDIR + "../build/post_proc_chimes_lsq.py"

    # Generic weight settings

    WEIGHTS_FORCE =   1.0

    REGRESS_ALG   = "dlasso"
    REGRESS_VAR   = "1.0E-5"
    REGRESS_NRM   = True

    # Job submitting settings (avoid defaults because they will lead to long queue times)

    CHIMES_BUILD_NODES = 2
    CHIMES_BUILD_QUEUE = "pdebug"
    CHIMES_BUILD_TIME  = "01:00:00"

    CHIMES_SOLVE_NODES = 2
    CHIMES_SOLVE_QUEUE = "pdebug"
    CHIMES_SOLVE_TIME  = "01:00:00"

    ################################
    ##### Molecular Dynamics
    ################################

    MD_STYLE        = "CHIMES"
    CHIMES_MD_MPI   = CHIMES_SRCDIR + "../build/chimes_md"

    MOLANAL         = CHIMES_SRCDIR + "../contrib/molanal/src/"
    MOLANAL_SPECIES = ["C1", "N1"]

    ################################
    ##### Hierarchical fitting block
    ################################

    DO_HIERARCH = True
    HIERARCH_PARAM_FILES = ['C.params.txt.reduced', 'N.params.txt.reduced']
    HIERARCH_EXE = CHIMES_MD_SER

    ################################
    ##### Single-Point QM
    ################################

    QM_FILES = WORKING_DIR + "ALL_BASE_FILES/QM_BASEFILES"
    VASP_EXE = "/usr/gapps/emc-vasp/vasp.5.4.4/build/gam/vasp"
    
The primary difference between the present ``config.py`` and that provided in the  file :ref:`page-basic` documentation are the highlighted lines 55--57, which specify hierarchical fitting should be performed (line 55), the name of all parameter files that the present model should be built upon (line 56), and the executable to use when evaluating contributions from the parameter files specified on line 56 (line 57); for this example, we're using ChIMES_MD. Note that this executable should be compiled for serial runs to prevent issues with the queueing system. As in the example provided in :ref:`page-basic` documentation, contents of the ``config.py`` file must be modified to reflect your e-mail address and absolute paths prior to running this example.


------------------------------------------
Running
------------------------------------------

-------

------------------------------------------
Inspecting the output
------------------------------------------

-------


========================================================
In-depth Setup and Options Overview
========================================================

For detailed instructions on setting up and running the ALD, see the :ref:`page-basic`
