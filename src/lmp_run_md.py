# Global (python) modules

import glob # Warning: glob is unserted... set my_list = sorted(glob.glob(<str>)) if sorting needed
import os
import random # Needed to set seed for each MD run

# Local modules

import helpers
import lmp_to_xyz
import cluster


def readframe(fstream,natoms):

    frame = []
    
    for i in range(natoms+9):
        
        frame.append(fstream.readline())
  
    return frame, frame[1]
    
def writeframe(frame, badness, badstream0, badstream1, badstream2):

    # Makes a .xyz file - assumes an orthorhombic box for now

    target = None
    
    if int(badness) == 0:
        target = badstream0
    elif int(badness) == 1:
        target = badstream1
    elif int(badness) == 2:
        target = badstream2
    else:
        print("Something strange happened... ")
        print("In writeframe, badness is:",badness)
        exit();
        
    boxl_x = frame[5]; boxl_x = boxl_x.split()[-1]
    boxl_y = frame[6]; boxl_y = boxl_y.split()[-1]
    boxl_z = frame[7]; boxl_z = boxl_z.split()[-1]
    
    xyz_text = []
    xyz_text.append(frame[3]) # Number of atoms
    xyz_text.append(boxl_x + " " + boxl_y + " " + boxl_z + '\n')
    
    fields = frame[8].split()
    
    elem = fields.index("element")-2
    xcrd = fields.index("xu")-2     
    ycrd = fields.index("yu")-2     
    zcrd = fields.index("zu")-2     
    
    for i in range(9,9+int(frame[3])):
    
        line = frame[i].split()
        xyz_text.append(line[elem] + " " + line[xcrd] + " " + line[ycrd] + " " + line[zcrd] + '\n')
    

    target.writelines(xyz_text)

def generate_trajbads():

    """ 
    
    Assumes traj.lammpstrj and rank-*.badness.log files are present in the current directory
    
    Generates the standard ChIMES_MD traj_bad.*.xyz files:
    
    - traj_bad_r.ge.rin+dp_dftbfrq.xyz
    - traj_bad_r.lt.rin+dp.xyz
    - traj_bad_r.lt.rin.xyz
    
    """
    
    # Sort badness data by step printed frame index

    helpers.cat_pattern("tmp-1.bad","rank-*badness.log")
    helpers.run_bash_cmnd_to_file("tmp-2.bad", "sort -nk1 tmp-1.bad")
    helpers.run_bash_cmnd_to_file("tmp-3.bad", "uniq tmp-2.bad")

    raw_badness = helpers.cat_to_var("tmp-3.bad")
    raw_badness = [i.split() for i in raw_badness]


    # Prepare to process the main trajectory file

    traj_stream  = open("traj.lammpstrj",'r')
    traj_natoms  = int(helpers.head("traj.lammpstrj",4)[-1])
    traj_frames  = int(helpers.wc_l("traj.lammpstrj")/(traj_natoms+9))

    #print("Expecting natoms per frame:", traj_natoms)
    #print("Expecting nframes:         ", traj_frames)


    # Create new files 

    bad_0_stream = open("traj_bad_r.ge.rin+dp_dftbfrq.xyz",'w')
    bad_1_stream = open("traj_bad_r.lt.rin+dp.xyz",'w')
    bad_2_stream = open("traj_bad_r.lt.rin.xyz",'w')


    # Process the files

    bad_idx_start   = 0
    bad_frame       = raw_badness[bad_idx_start][0]

    for i in range(traj_frames):

        # Read the frame
        
        #print("\n****Working on frame:",i)

        contents,frame = readframe(traj_stream,traj_natoms)

        # Determine the frame badness

        badness = raw_badness[bad_idx_start][1] # Get the first badness assigned to this frame
        
        #print("here:",int(badness), "note:",len(raw_badness))
        
        for j in range(bad_idx_start, len(raw_badness)):
        
            #print("trying i,j:",i,j,"; raw has frame:",raw_badness[j][0], "trj has frame:",frame)
        
            if int(raw_badness[j][0]) != int(frame):
                bad_idx_start = j
                #print("\tBreaking - set start to:",bad_idx_start)
                break
            
            elif int(raw_badness[j][1]) >= int(badness):
                #print("\tUpdating badness to:",raw_badness[j][1])
                badness = raw_badness[j][1]
            else:
                print("\tSomething strange happened...")
                
                print(raw_badness[j])
                print("\tWhile working on frame  ",i)
                print("\tj is              ",j)
                print("\tj's badness is:   ", raw_badness[j][1])
                print("\tCurrent badness is:" ,badness)  
                
                exit()
                

        # Print the frame to the correct file

        writeframe(contents, badness, bad_0_stream, bad_1_stream, bad_2_stream)

    bad_0_stream.close()
    bad_1_stream.close()
    bad_2_stream.close()   

    helpers.run_bash_cmnd("rm -f traj-1.bad")
    helpers.run_bash_cmnd("rm -f traj-1.bad")
    helpers.run_bash_cmnd("rm -f traj-1.bad")
        
    

def post_proc(my_ALC, my_case, my_indep, *argv, **kwargs):

    """ 
    
    Post-processes a LAMMPS MD run (i.e., using (a) ChIMES parameter file(s))
    
    Usage: run_md(1, 0, 0, <arguments>)
    
    Notes: See function definition in run_md.py for a full list of options. 
           Requrires config.CHIMES_MOLANAL (should contain molanal.new and findmolecules.pl)
           Expects to be called from ALC-my_ALC's base folder.
           Assumes job is being launched from ALC-X.
           Supports ~parallel learning~ via file structure:
                  ALC-X/CASE-1_INDEP-1/<md simulation/stuff>
           Expects input files named like:
                  case-1.indep-1.input.xyz and case-1.indep-1.run_md.in
           will run molanal on finished simulation.
           Will post-process the molanal output.
           Will generate clusters.
           Will save clusters to CASE-X_INDEP-0/CFG_REPO.
           
    """
    
    ################################
    # 0. Set up an argument parser
    ################################
    
    ### ...argv
    
    args_species = argv[0] # This is a pointer!
    
    ### ...kwargs
    
    default_keys   = [""]*5
    default_values = [""]*5


    # MD specific controls
    
    default_keys[0 ] = "basefile_dir"  ; default_values[0 ] = "../CHIMES-MD_BASEFILES/" # Directory containing run_md.base, etc.
    default_keys[1 ] = "driver_dir"    ; default_values[1 ] = ""                        # Post_proc_lsq*py file... should also include the python command
    default_keys[2 ] = "penalty_pref"  ; default_values[2 ] = 1.0E6                     # Penalty function pre-factor
    default_keys[3 ] = "penalty_dist"  ; default_values[3 ] = 0.02                      # Pentaly function kick-in distance
    default_keys[4 ] = "local_python"  ; default_values[4 ] = ""                        # Local computer's python executable
        
    args = dict(list(zip(default_keys, default_values)))
    args.update(kwargs)
    
    ################################
    # 1. Move to the MD directory
    ################################
    
    my_md_path = "CASE-" + str(my_case) + "_INDEP_" + str(my_indep) + "/"
    
    os.chdir(my_md_path)
    
    ################################
    # 1. Run molanal
    ################################
    
    # Convert the resulting trajectory file to .gen file named traj.gen
    
    lmp_to_xyz.lmp_to_xyzf("REAL", "traj.lammpstrj", "log.lammps") # Creates a file called traj.lammptrj.xyzf
    helpers.xyz_to_dftbgen("traj.lammpstrj.xyzf") # Creates a file named traj.lammpstrj.gen
    helpers.run_bash_cmnd("mv traj.lammpstrj.gen traj.gen")
 
    if os.path.isfile(args["basefile_dir"] + "case-" + str(my_case) + ".skip.dat"):
    
        helpers.run_bash_cmnd("cp " + args["basefile_dir"] + "case-" + str(my_case) + ".skip.dat skip.dat")
    
    
    helpers.run_bash_cmnd_to_file("traj.gen-molanal.out",args["molanal_dir"] + "/molanal.new traj.gen")
    helpers.run_bash_cmnd_to_file("traj.gen-find_molecs.out", args["molanal_dir"] + "/findmolecules.pl traj.gen-molanal.out")
    helpers.run_bash_cmnd("rm -rf molecules " + ' '.join(glob.glob("molanal*")))
    
    print(helpers.run_bash_cmnd_presplit([args["local_python"], args["driver_dir"] + "/src/post_process_molanal.py"] + args_species))
    
    ################################
    # 2. Don't cluster, but use it's file paring utility to grab candidate 20F trajectories
    ################################
    
    generate_trajbads()
    cluster.get_pared_trajs(False) # Argument: We will not prepare for cluster analysis, since it is incompatible with LAMMPS
        

    os.chdir("..")
    
    return     


def run_md(my_ALC, my_case, my_indep, *argv, **kwargs):

    """ 
    
    Launches a LAMMPS md simulation
    
    Usage: run_md(1, 0, 0, <arguments>)
    
    Notes: See function definition in helpers.py for a full list of options. 
           Requrires config.LAMMPS_MD to be set.
           Expects to be called from ALC-my_ALC's base folder.
           Assumes job is being launched from ALC-X.
           Supports ~parallel learning~ via file structure:
                  ALC-X/CASE-1_INDEP-1/<md simulation/stuff>
           Expects input files named like:
                  case-1.indep-1.data.in and case-1.indep-1.in.lammps
           Returns a job_id for the submitted job.
           
           Does NOT support ChIMES cluster entropy-based active learning!
               
    """
    
    ################################
    # 0. Set up an argument parser
    ################################
    
    ### ...argv
    
    args_species = argv # This is a pointer!
    
    ### ...kwargs
    
    default_keys   = [""]*16
    default_values = [""]*16

    # MD specific controls

    default_keys[0 ] = "basefile_dir"  ; default_values[0 ] = "../LMP-MD_BASEFILES/"    # Directory containing run_md.base, etc.
    default_keys[1 ] = "driver_dir"    ; default_values[1 ] = ""                           # Post_proc_lsq*py file... should also include the python command
    default_keys[2 ] = "penalty_pref"  ; default_values[2 ] = 1.0E6                        # Penalty function pre-factor
    default_keys[3 ] = "penalty_dist"  ; default_values[3 ] = 0.02                         # Pentaly function kick-in distance
    default_keys[4 ] = "chimes_exe  "  ; default_values[4 ] = None                         # Unused by this function
    
    # Overall job controls

    default_keys[5 ] = "job_name"      ; default_values[5 ] = "ALC-"+ repr(my_ALC)+"-md"     # Name for ChIMES md job
    default_keys[6 ] = "job_nodes"     ; default_values[6 ] = "2"                            # Number of nodes for ChIMES md job
    default_keys[7 ] = "job_ppn"       ; default_values[7 ] = "36"                           # Number of processors per node for ChIMES md job
    default_keys[8 ] = "job_walltime"  ; default_values[8 ] = "1"                            # Walltime in hours for ChIMES md job
    default_keys[9 ] = "job_queue"     ; default_values[9 ] = "pdebug"                       # Queue for ChIMES md job
    default_keys[10] = "job_account"   ; default_values[10] = "pbronze"                      # Account for ChIMES md job
    default_keys[11] = "job_executable"; default_values[11] = ""                             # Full path to executable for ChIMES md job
    default_keys[12] = "job_system"    ; default_values[12] = "slurm"                        # slurm or torque    
    default_keys[13] = "job_file"      ; default_values[13] = "run.cmd"                      # Name of the resulting submit script
    default_keys[14] = "job_email"     ; default_values[14] = True                           # Send slurm emails?
    default_keys[15] = "job_modules"   ; default_values[15] = ""                             # Send slurm emails?

    args = dict(list(zip(default_keys, default_values)))
    args.update(kwargs)    
    
    ################################
    # 1. Create the MD directory for this specific case and independent simulation, grab the base files
    ################################
    
    my_md_path = "CASE-" + str(my_case) + "_INDEP_" + str(my_indep) + "/"

    helpers.run_bash_cmnd("rm -rf " + my_md_path)
    helpers.run_bash_cmnd("mkdir -p " + my_md_path)

    #helpers.run_bash_cmnd("cp "+ ' '.join(glob.glob(args["basefile_dir"] + "/*"  )) + " " + my_md_path)
    helpers.run_bash_cmnd("cp "+ ' '.join(glob.glob(args["basefile_dir"] + "/case-" + str(my_case) + ".indep-" + str(my_indep) + "*" )) + " " + my_md_path)
    helpers.run_bash_cmnd("cp GEN_FF/params.txt.reduced " + my_md_path)
    

    ################################
    # 2. Post-process the parameter file
    ################################
    
    os.chdir(my_md_path)


    ifstream   = open("params.txt.reduced",'r')
    paramsfile = ifstream.readlines()

    ofstream = open("tmp",'w')
    
    found = False
        
    for i in range(len(paramsfile)):
    
        if found:
            ofstream.write(paramsfile[i])
            ofstream.write("PAIR CHEBYSHEV PENALTY DIST:    " + str(args["penalty_dist"]) + '\n')
            ofstream.write("PAIR CHEBYSHEV PENALTY SCALING: " + str(args["penalty_pref"]) + '\n\n')

            found = False
        else:
            
            ofstream.write(paramsfile[i])
            
            if "FCUT TYPE" in paramsfile[i]:
                found  = True
    ofstream.close()
    helpers.run_bash_cmnd("mv tmp params.txt.reduced")
    
    
    ################################
    # 3. Post-process the run_md.in file
    ################################
    
    md_infile  = "case-" + str(my_case) + ".indep-" + str(my_indep) + ".in.lammps"
    md_xyzfile = "case-" + str(my_case) + ".indep-" + str(my_indep) + ".data.in"    
    
    ifstream = open(md_infile,'r')
    runfile  = ifstream.readlines()
    
    ofstream = open("tmp",'w')    
        
    for i in range(len(runfile)):
        
        # Set seed (velocity all create)
    
        if "seed equal" in runfile[i]:
            ofstream.write("variable seed equal " + str(random.randint(0,9999)) + '\n')          
        else:
            ofstream.write(runfile[i])
                
    ofstream.close()
    helpers.run_bash_cmnd("mv tmp " + md_infile)

    
    ################################
    # 4. Launch the md simulation
    ################################
    
    # Create the task string
    
    job_task = ""
    

    if args["job_system"] == "slurm":
        job_task += "srun -N "   + repr(int(args["job_nodes" ])) + " -n " + repr(int(args["job_nodes"])*int(args["job_ppn"])) + " "
    else:
        job_task += "mpirun -np" + repr(int(args["job_nodes" ])) + " -n " + repr(int(args["job_nodes"])*int(args["job_ppn"])) + " "
        
    job_task += args["job_executable"] + " -i " + md_infile + "  > out.lammps"
         
    
    md_jobid = helpers.create_and_launch_job(
        job_name       =     args["job_name"    ] ,
        job_email      =     args["job_email"   ] ,
        job_nodes      = str(args["job_nodes"   ]),
        job_ppn        = str(args["job_ppn"     ]),
        job_walltime   = str(args["job_walltime"]),
        job_queue      =     args["job_queue"   ] ,
        job_account    =     args["job_account" ] ,
        job_executable =     job_task,
        job_system     =     args["job_system"  ] ,
        job_modules    =     args["job_modules" ] ,
        job_file       =     "run_lmpmd.cmd")
        
    
    os.chdir("..")
    
    return md_jobid    
    
