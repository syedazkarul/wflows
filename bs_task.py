from __future__ import  division, unicode_literals, print_function

import glob
import os
import shutil
import logging
from pymatgen.core import Structure
from pymatgen.io.vasp.sets import MPRelaxSet, MPStaticSet, MPNonSCFSet, MVLElasticSet
from custodian.custodian import Custodian
from fireworks.core.firework import FiretaskBase, FWAction
from fireworks.utilities.fw_utilities import explicit_serialize
from monty.json import MontyDecoder
from custodian.vasp.handlers import VaspErrorHandler, MeshSymmetryErrorHandler, PotimErrorHandler, \
    NonConvergingErrorHandler, UnconvergedErrorHandler
from custodian.vasp.validators import VasprunXMLValidator

__author__ = 'Zhenbin Wang'
__date__ = "3/20/17"
__email__="z9wang at ucsd.edu"


@explicit_serialize
class MPRelaxationVASPInputTask(FiretaskBase):
    """
    Run structure relaxation w/ MP params.
    """

    required_params = ["structure"]

    def run_task(self, fw_spec):
        struct = self.get("structure") or fw_spec["structure"]
        s = Structure.from_dict(struct.as_dict())
        user_incar_settings = fw_spec.get("user_incar_settings", {})
        vasp_input_set = MPRelaxSet(s, user_incar_settings=user_incar_settings)
        dec = MontyDecoder()
        vis = dec.process_decoded(vasp_input_set.as_dict())
        output_dir = os.getcwd()
        vis.write_input(output_dir=output_dir)
        return FWAction()


@explicit_serialize
class MPStaticVASPInputTask(FiretaskBase):
    """
    Perform static run w/ MP params.
    """

    required_params = ["material_id"]

    def run_task(self, fw_spec):
        material_id = self["material_id"]
        dest_root = fw_spec["_fw_en"]["run_dest_root"]
        dest = "{}/{}/bs/{}/relax".format(dest_root, os.environ["USER"], material_id)
        user_incar_settings = fw_spec.get("user_incar_settings", {})
        vasp_input_set = MPStaticSet.from_prev_calc(prev_calc_dir=dest,
                                                    standardize=1e-3,
                                                    user_incar_settings=user_incar_settings)
        dec = MontyDecoder()
        vis = dec.process_decoded(vasp_input_set.as_dict())
        vis.write_input(".")


@explicit_serialize
class MPNonSCFVASPInputTask(FiretaskBase):
    """
    Do non-scf (band structure and density of state) calculations.
    """

    required_params = ["material_id", "mode"]

    def run_task(self, fw_spec):
        material_id = self["material_id"]
        mode = self["mode"]
        dest_root = fw_spec["_fw_env"]["run_dest_root"]
        dest = "{}/{}/bs/{}/static".format(dest_root, os.environ["USER"], material_id)
        user_incar_settings = fw_spec.get("user_incar_settings", {})
        if mode.lower() == "line":
            vasp_input_set = MPNonSCFSet.from_prev_calc(dest, standardize=1e-3,
                                                        user_incar_settings=user_incar_settings,
                                                        mode=mode)
            dec = MontyDecoder()
            vis = dec.process_decoded(vasp_input_set.as_dict())
            vis.write_input(".")
        elif mode.lower() == "uniform":
            vasp_input_set = MPNonSCFSet.from_prev_calc(dest,
                                                        user_incar_settings=user_incar_settings,
                                                        mode=mode)
            dec = MontyDecoder()
            vis = dec.process_decoded(vasp_input_set.as_dict())
            vis.write_input(".")


@explicit_serialize
class RunCustodianTask(FiretaskBase):
    """
    Use custodian to monitor the jobs
    """

    required_params = ["jobs"]
    optional_params = ["custodian_params"]

    def run_task(self, fw_spec):
        dec = MontyDecoder()
        jobs = dec.process_decoded(self["jobs"])
        fw_env = fw_spec.get("_fw_env", {})
        #Override VASP and gamma VASP commands using fw_env
        if fw_env.get("vasp_cmd"):
            for j in jobs:
                j.vasp_cmd = os.path.expandvars(fw_env["vasp_cmd"])
                j.gamma_vasp_cmd = j.gamma_vasp_cmd
                logging.info("Vasp command is {}".format(j.vasp_cmd))
        if fw_env.get("gamma_vasp_cmd"):
            for j in jobs:
                j.gamma_vasp_cmd = os.path.expandvars(fw_env["gamma_vasp_cmd"])
                logging.info("Vasp gamma command is {}".format(j.gamma_vasp_cmd))
        #Override custodian scratch dir.
        cust_params = self.get("custodian_params", {})
        if fw_env.get("scratch_root"):
            cust_params["scratch_dir"] = os.path.expandvars(fw_env["scratch_root"])

        logging.info("Running with custodian params %s" % cust_params)
        handlers = [VaspErrorHandler(), MeshSymmetryErrorHandler(),
                    UnconvergedErrorHandler(), NonConvergingErrorHandler(),
                    PotimErrorHandler()]
        validators = [VasprunXMLValidator()]
        c = Custodian(handlers=[h.as_dict() for h in handlers],
                      jobs=jobs,
                      validators=[v.as_dict() for v in validators],
                      **cust_params)
        output = c.run()
        return FWAction(stored_data=output)


@explicit_serialize
class TransferResultsTask(FiretaskBase):
    """
    Save calculated results
    """

    required_params = ["material_id", "job_type"]

    def run_task(self, fw_spec):
        material_id = self.get("material_id") or fw_spec["material_id"]
        job_type = self["job_type"]
        dest_root = fw_spec["_fw_env"]["run_dest_root"]
        dest = "{}/{}/bs/{}/{}".format(dest_root, os.environ["USER"], material_id, job_type)
        existing = glob.glob(dest, "/*")
        if not existing:
            dest = dest
        else:
            dest += "_0"

        src = os.path.abspath(".")
        shutil.copytree(src, dest)

        for f in os.listdir(src):
            try:
                os.remove(os.path.join(src, f))
            except:
                pass
