from __future__ import print_function, division
from pymatgen.io.vasp.sets import MPRelaxSet
from pymatgen.io.vasp import Kpoints
import math

__author__ = 'wzb'
__email__ = 'z9wang at ucsd.edu'
__date__ = '03/20/17'


class SOFCVaspInputSet(MPRelaxSet):
    """
    for sofcs calc.
    """

    def __init__(self, structure, min_length=10, **kwargs):
        user_incar_settings = kwargs.get("user_incar_settings", {})
        defaults = {"EDIFF": 1e-4,
                    "EDIFFG": -0.03,
                    "ISIF": 2,
                    "NELMIN": 5,
                    "ISMEAR": 0,
                    "LCHARG": "False",
                    "NSW": 500}
        defaults.update(user_incar_settings)
        kwargs["user_incar_settings"] = defaults
        super(SOFCVaspInputSet, self).__init__(structure, **kwargs)
        self.min_length = min_length

    @property
    def kpoints(self):

        """
        create k-points for surface/interface structure relaxation.
        """

        kpt = super(SOFCVaspInputSet, self).kpoints
        kpt.comment = "Automatic mesh"
        lengths = self.structure.lattice.abc
        kpt_calc = [max(1, int(round(math.ceil(self.min_length / x)))) for x in lengths]
        if kpt_calc == [1, 1, 1]:
            kpt.style = Kpoints.supported_modes.Gamma
            kpt.kpts[0] = kpt_calc
        else:
            kpt.kpts[0] = kpt_calc
        return kpt
