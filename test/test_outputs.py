
"""
Test sanity of various output formats for a minimal real-world example.
"""
from __future__ import print_function

import subprocess
import tempfile
import unittest
import os.path
import csv
import re

import h5py


os.environ["PACBIO_TEST_ENV"] = "1" # turns off --verbose

DATA_DIR = "/pbi/dept/secondary/siv/testdata/kineticsTools"
REF_DIR = "/pbi/dept/secondary/siv/references/Helicobacter_pylori_J99"
ALIGNMENTS = os.path.join(DATA_DIR, "Hpyl_1_5000.xml")
REFERENCE = os.path.join(REF_DIR, "sequence", "Helicobacter_pylori_J99.fasta")

skip_if_no_data = unittest.skipUnless(
    os.path.isdir(DATA_DIR) and os.path.isdir(REF_DIR),
    "%s or %s not available" % (DATA_DIR, REF_DIR))

@skip_if_no_data
class TestOutputs(unittest.TestCase):

    @classmethod
    @skip_if_no_data
    def setUpClass(cls):
        prefix = tempfile.NamedTemporaryFile().name
        cls.h5_file = "{p}.h5".format(p=prefix)
        cls.csv_file = "{p}.csv".format(p=prefix)
        cls.gff_file = "{p}.gff".format(p=prefix)
        cls.bw_file = "{p}.bw".format(p=prefix)
        args = [
            "ipdSummary", "--log-level", "WARNING",
            "--csv_h5", cls.h5_file,
            "--csv", cls.csv_file,
            "--gff", cls.gff_file,
            "--bigwig", cls.bw_file,
            "--numWorkers", "12",
            "--pvalue", "0.001",
            "--identify", "m6A,m4C",
            "--referenceStride", "100",
            "--referenceWindows", "gi|12057207|gb|AE001439.1|:0-200",
            "--reference", REFERENCE,
            ALIGNMENTS
        ]
        print(" ".join(args))
        assert subprocess.call(args) == 0
        with open(cls.csv_file) as f:
            cls.csv_records = [l.split(",") for l in f.read().splitlines()][1:]

    @classmethod
    def tearDownClass(cls):
        return
        for fn in [cls.h5_file, cls.csv_file, cls.gff_file, cls.bw_file]:
            if os.path.exists(fn):
                os.remove(fn)

    def test_h5_output(self):
        f = h5py.File(self.h5_file)
        g = f[f.keys()[0]] # just one group in this file
        bases = g['base'].__array__()
        self.assertEqual(bases[0], "A")
        self.assertEqual(bases[100], "T")
        self.assertEqual(list(bases[0:400] != "").count(True), 400)
        seqh_fwd = ''.join([g['base'][x*2] for x in range(200)])
        seqc_fwd = ''.join([self.csv_records[x*2][3] for x in range(200)])
        self.assertEqual(seqh_fwd, seqc_fwd)
        seqh_rev = ''.join([g['base'][(x*2)+1] for x in range(200)])
        seqc_rev = ''.join([self.csv_records[(x*2)+1][3] for x in range(200)])
        self.assertEqual(seqh_rev, seqc_rev)
        tpl_fwd = [g['tpl'][x*2] for x in range(200)]
        self.assertEqual(tpl_fwd, range(1, 201))
        f = h5py.File(self.h5_file)
        for i_rec, rec in enumerate(self.csv_records):
            self.assertEqual(str(g['tpl'][i_rec]), self.csv_records[i_rec][1])
            self.assertEqual("%.3f"%g['ipdRatio'][i_rec],
                             self.csv_records[i_rec][8])

    def test_csv_output(self):
        self.assertEqual(len(self.csv_records), 400)
        self.assertEqual(self.csv_records[0][3], "A")
        self.assertEqual(self.csv_records[100][3], "T")

    def test_bigwig(self):
        import pyBigWig
        f = pyBigWig.open(self.bw_file)
        for i_rec, rec in enumerate(self.csv_records):
            seqid = re.sub('\"', "", rec[0])
            tpl = int(rec[1]) - 1
            s = int(f.values(seqid, tpl, tpl+1)[0])
            ipd_minus = (s % 65536) / 100.0
            ipd_plus = (s >> 16) / 100.0
            if rec[2] == "1":
                self.assertAlmostEqual(ipd_minus, float(rec[8]), places=1)
            else:
                self.assertAlmostEqual(ipd_plus, float(rec[8]), places=1)


if __name__ == "__main__":
    unittest.main()
