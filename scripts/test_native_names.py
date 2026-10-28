"""Regression check for the Python native checker: python scripts/test_native_names.py."""
import contextlib
import io
import json
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace

import lint_lua
import native_names
import nativedb
from i18n import t


def metadata(name, native_hash):
    return {"lua": name, "name": name, "hash": native_hash, "params": [{"name": "toggle", "type": "BOOL"}],
            "results": "void", "apiset": "client", "ns": "GRAPHICS", "aliases": []}


def main():
    with tempfile.TemporaryDirectory(prefix="native-names-") as directory:
        root = Path(directory)
        client = """function Global.SetForceVehicleTrails(toggle)
    return _in(0x4CC7F0FEA5283FE0, toggle)
end
function Global.GetGroundZFor_3dCoord(x, y, z, includeWater)
    return _in(0xC906A7DAB05C8D2B, x, y, z, includeWater)
end
function Global.SetDifferentNative(entity)
    return _in(0x11, entity)
end
function Global.GetBlipSprite(blip)
    return _in(0x44, blip)
end
function Global.SetRuntimeOnly(entity)
    return _in(0x66, entity)
end
Global.N_0x4cc7f0fea5283fe0 = Global.SetForceVehicleTrails
Global.SetActualAlias = Global.SetForceVehicleTrails
Global.SetAlternateName = Global.SetDifferentNative
"""
        server = """function Global.SetDifferentNative()
    return _in(0x22)
end
function Global.GetBlipSprite(self)
    return _in(0x55, self)
end
function Global.SetRuntimeOnly()
    return _in(0x77)
end
"""
        (root / "natives_universal.lua").write_text(client, encoding="utf-8")
        (root / "natives_server.lua").write_text(server, encoding="utf-8")
        bindings, sources = native_names.runtime_bindings(root)
        raw = {
            "_SetForceVehicleTrails": metadata("_SetForceVehicleTrails", "0x4CC7F0FEA5283FE0"),
            "GetGroundZFor3dCoord": metadata("GetGroundZFor3dCoord", "0xC906A7DAB05C8D2B"),
            "_SetDifferentNative": metadata("_SetDifferentNative", "0x11"),
            "SetDifferentNative": metadata("SetDifferentNative", "0x22"),
            "SetMetadataOnly": metadata("SetMetadataOnly", "0x33"),
            "GetBlipSprite": metadata("GetBlipSprite", "0x55"),
        }
        records = native_names.apply_runtime_names(raw, bindings)
        index = native_names.callable_index(records)
        assert "SetForceVehicleTrails" in index and "_SetForceVehicleTrails" not in index
        assert "GetGroundZFor_3dCoord" in index and "GetGroundZFor3dCoord" not in index
        assert "SetActualAlias" in index and "N_0x4cc7f0fea5283fe0" in index
        assert "SetMetadataOnly" not in index
        assert sources["client"]["names"] == 8
        assert records == native_names.apply_runtime_names(records, bindings)
        for side, expected_hash, count in [("client", 0x11, 1), ("server", 0x22, 0)]:
            selected = native_names.binding_record(index["SetDifferentNative"], "SetDifferentNative", side)
            assert int(selected["hash"], 16) == expected_hash
            assert len(selected["params"]) == count
            selected = native_names.reference_record(index["SetDifferentNative"], hex(expected_hash))
            assert int(selected["hash"], 16) == expected_hash and selected["apiset"] == side
        for name, client_hash, server_hash in [("GetBlipSprite", 0x44, 0x55), ("SetRuntimeOnly", 0x66, 0x77)]:
            for side, expected_hash in [("client", client_hash), ("server", server_hash)]:
                selected = native_names.binding_record(index[name], name, side)
                assert int(selected["hash"], 16) == expected_hash

        nativedb._DB = records
        options = SimpleNamespace(names=["SetForceVehicleTrails"], apiset=None, json=True)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            assert nativedb.cmd_check(options) == 0
        assert json.loads(output.getvalue())[0]["exists"]
        for wrong in ["_SetForceVehicleTrails", "GetGroundZFor3dCoord", "setforcevehicletrails", "SetMetadataOnly"]:
            options.names = [wrong]
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                assert nativedb.cmd_check(options) == 1
            result = json.loads(output.getvalue())[0]
            assert not result["exists"]
            assert all(suggestion in index for suggestion in result["suggestions"])
        options.names = ["SetForceVehicleTrails"]
        options.apiset = "server"
        with contextlib.redirect_stdout(io.StringIO()):
            assert nativedb.cmd_check(options) == 1
        options.names = ["0x22"]
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            assert nativedb.cmd_check(options) == 0
        assert int(json.loads(output.getvalue())[0]["hash"], 16) == 0x22

        snippet = root / "client.lua"
        snippet.write_text("SetForceVehicleTrails(false)\n_SetForceVehicleTrails(false)\nGetGroundZFor3dCoord(1, 2, 3)\n", encoding="utf-8")
        _, findings = lint_lua.lint_file(str(snippet), index, "client")
        errors = [finding for finding in findings if finding["rule"] == "E001"]
        assert {finding["native"] for finding in errors} == {"_SetForceVehicleTrails", "GetGroundZFor3dCoord"}
        assert all("_SetForceVehicleTrails?" not in finding["message"] for finding in errors)
        assert "SetForceVehicleTrails" in errors[0]["message"]
        snippet.write_text("SetForceVehicleTrails(false)\n", encoding="utf-8")
        _, findings = lint_lua.lint_file(str(snippet), index, "server")
        assert any(finding["rule"] == "E002" for finding in findings)
        with contextlib.redirect_stderr(io.StringIO()):
            try:
                native_names.load_database(root / "missing.json")
                raise AssertionError("Missing metadata was accepted")
            except SystemExit as error:
                assert error.code == 2
            (root / "invalid.json").write_text("{", encoding="utf-8")
            try:
                native_names.load_database(root / "invalid.json")
                raise AssertionError("Malformed metadata was accepted")
            except SystemExit as error:
                assert error.code == 3
            try:
                native_names.runtime_bindings(root / "missing")
                raise AssertionError("Missing runtime was accepted")
            except SystemExit as error:
                assert error.code == 2
        (root / "natives_universal.lua").write_text("not a wrapper", encoding="utf-8")
        with contextlib.redirect_stderr(io.StringIO()):
            try:
                native_names.runtime_bindings(root)
                raise AssertionError("Malformed runtime was accepted")
            except SystemExit as error:
                assert error.code == 3
    assert not os.path.exists(directory)
    print(t("native_tests_passed"))


if __name__ == "__main__":
    main()
