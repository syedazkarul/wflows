from __future__ import  division, unicode_literals, print_function


import os
from pymatgen.core import Structure
from custodian.vasp.jobs import VaspJob
from fireworks.core.firework import Firework, Workflow
from fireworks.core.launchpad import LaunchPad
from bs_wflows.bs_task import MPRelaxationVASPInputTask, MPStaticVASPInputTask, MPNonSCFVASPInputTask, \
    RunCustodianTask, TransferResultsTask


__author__ = 'Zhenbin Wang'
__date__ = "3/20/17"
__email__="z9wang at ucsd.edu"

MODULE_DIR = os.path.dirname(os.path.abspath(__file__))

launchpad = LaunchPad.from_file(os.path.join(os.environ["HOME"], ".fireworks", "my_launchpad.yaml"))

struct_file = os.path.join(MODULE_DIR, "test_files/ICSD_182730_Si.cif")
material_id = "material_id"
s = Structure.from_file(struct_file)

vasp_jobs = VaspJob(["srun", "-n", "32", "-c", "16", "--cpu_bind=cores", "vasp_std"], auto_npar=False)
double_relaxations = VaspJob.double_relaxation_run(vasp_cmd=vasp_jobs, auto_npar=False)

scratch_dir = "/global/cscratch1/sd/{}/temp_project".format(os.environ["USER"])

fw1 = Firework([MPRelaxationVASPInputTask(structure=s.as_dict()),
                RunCustodianTask(jobs=[j.as_dict() for j in double_relaxations],
                                 custodian_params={"scratch_dir": scratch_dir}),
                TransferResultsTask(material_id=material_id,
                                    job_type="relax")],
                name="{} MP Relax".format(material_id))

fw2 = Firework([MPStaticVASPInputTask(material_id=material_id),
                RunCustodianTask(jobs=[vasp_jobs.as_dict()],
                                 custodian_params={"scratch_dir": scratch_dir}),
                TransferResultsTask(material_id=material_id,
                                    job_type="static")],
               name="{} MP Static".format(material_id))

fw3 = Firework([MPNonSCFVASPInputTask(material_id=material_id, mode="line"),
               RunCustodianTask(jobs=[vasp_jobs.as_dict()],
                                custodian_params={"scratch_dir": scratch_dir}),
               TransferResultsTask(material_id=material_id,
                                   job_type="band")],
               name="{} MP Band".format(material_id))

fw4 = Firework([MPNonSCFVASPInputTask(material_id=material_id, mode="uniform"),
               RunCustodianTask(jobs=[vasp_jobs.as_dict()],
                                custodian_params={"scratch_dir": scratch_dir}),
               TransferResultsTask(material_id=material_id,
                                   job_type="dos")],
               name="{} MP Dos".format(material_id))

workflows = Workflow([fw1, fw2, fw3, fw4], {fw1: [fw2], fw2: [fw3, fw4]}, name="BS Workflow")
launchpad.add_wf(workflows)
