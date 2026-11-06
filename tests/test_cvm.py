import csv
import io
import zipfile

import pytest

from b3desk.importers import cvm_filing


def make_zip(path, duplicate=False):
    fields = [
        "CD_CVM",
        "DT_REFER",
        "DT_FIM_EXERC",
        "ORDEM_EXERC",
        "CD_CONTA",
        "ESCALA_MOEDA",
        "MOEDA",
        "VL_CONTA",
    ]
    with zipfile.ZipFile(path, "w") as archive:
        for statement, accounts in {
            "DRE": [("3.01", "100"), ("3.11", "20")],
            "BPP": [("2.03", "200")],
        }.items():
            stream = io.StringIO()
            writer = csv.writer(stream, delimiter=";")
            writer.writerow(fields)
            for account, value in accounts + (accounts if duplicate else []):
                writer.writerow(
                    [123, "2023-12-31", "2023-12-31", "ÚLTIMO", account, "MIL", "REAL", value]
                )
            archive.writestr(
                f"dfp_cia_aberta_{statement}_con_2023.csv", stream.getvalue().encode("latin-1")
            )


def test_cvm_units_accounts_and_publication(tmp_path):
    path = tmp_path / "dfp.zip"
    make_zip(path)
    filing = cvm_filing(path, 123, "2023-12-31", "2024-03-01")
    assert filing.revenue == 100_000
    assert filing.net_income == 20_000
    assert filing.equity == 200_000
    assert filing.available_on == "2024-03-01"
    with pytest.raises(ValueError, match="Missing"):
        cvm_filing(path, 456, "2023-12-31", "2024-03-01")


def test_ambiguous_revisions_rejected(tmp_path):
    path = tmp_path / "dfp.zip"
    make_zip(path, duplicate=True)
    with pytest.raises(ValueError, match="Ambiguous"):
        cvm_filing(path, 123, "2023-12-31", "2024-03-01")
