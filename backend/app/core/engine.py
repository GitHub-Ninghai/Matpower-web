"""
Octave/MATPOWER Simulation Engine
Core module for interfacing with GNU Octave and MATPOWER via subprocess
"""
import json
import logging
import os
import re
import subprocess
import tempfile
import time
import copy
from pathlib import Path
from typing import List, Dict, Any, Optional

import numpy as np

from app.core.config import settings, get_matpower_path, get_data_path

logger = logging.getLogger(__name__)

# Octave CLI path
OCTAVE_BIN = os.path.join(
    os.environ.get("OCTAVE_HOME", ""),
    "mingw64", "bin", "octave-cli-11.1.0.exe"
)

# Try common locations
if not os.path.isfile(OCTAVE_BIN):
    _candidates = [
        r"C:\Users\10532\AppData\Local\Programs\GNU Octave\Octave-11.1.0\mingw64\bin\octave-cli-11.1.0.exe",
        r"C:\Program Files\GNU Octave\Octave-11.1.0\mingw64\bin\octave-cli-11.1.0.exe",
    ]
    for _c in _candidates:
        if os.path.isfile(_c):
            OCTAVE_BIN = _c
            break


class OctaveEngine:
    """
    Octave/MATPOWER Simulation Engine via subprocess.
    Generates Octave scripts, runs them, and parses JSON output.
    """

    # Column definitions for MATPOWER matrices
    BUS_COLUMNS = {
        'bus_i': 0, 'bus_type': 1, 'pd': 2, 'qd': 3, 'gs': 4, 'bs': 5,
        'area': 6, 'vm': 7, 'va': 8, 'base_kv': 9, 'zone': 10,
        'vmax': 11, 'vmin': 12, 'lam_p': 13, 'lam_q': 14,
        'mu_vmax': 15, 'mu_vmin': 16
    }

    GEN_COLUMNS = {
        'gen_bus': 0, 'pg': 1, 'qg': 2, 'qmax': 3, 'qmin': 4, 'vg': 5,
        'mbase': 6, 'gen_status': 7, 'pmax': 8, 'pmin': 9, 'pc1': 10,
        'pc2': 11, 'qc1min': 12, 'qc1max': 13, 'qc2min': 14, 'qc2max': 15,
        'ramp_agc': 16, 'ramp_10': 17, 'ramp_30': 18, 'ramp_q': 19,
        'apf': 20
    }

    BRANCH_COLUMNS = {
        'f_bus': 0, 't_bus': 1, 'br_r': 2, 'br_x': 3, 'br_b': 4,
        'rate_a': 5, 'rate_b': 6, 'rate_c': 7, 'tap': 8, 'shift': 9,
        'br_status': 10, 'angmin': 11, 'angmax': 12, 'pf': 13, 'qf': 14,
        'pt': 15, 'qt': 16
    }

    def __init__(self):
        self.matpower_path = str(get_matpower_path()).replace("\\", "/")
        self.data_path = str(get_data_path()).replace("\\", "/")
        self.octave_bin = OCTAVE_BIN
        self.is_initialized = False
        self._check_octave()

    def _check_octave(self):
        """Check if Octave is available"""
        if os.path.isfile(self.octave_bin):
            logger.info(f"Octave found at: {self.octave_bin}")
            self.is_initialized = True
        else:
            logger.error(f"Octave not found at: {self.octave_bin}")
            self.is_initialized = False

    def _run_octave_script(self, script: str, timeout: int = 60) -> Dict[str, Any]:
        """
        Run an Octave script via subprocess and parse JSON output.
        The script must write results to a JSON file.
        """
        with tempfile.NamedTemporaryFile(mode='w', suffix='.m', delete=False, encoding='utf-8') as f:
            f.write(script)
            script_path = f.name

        result_json = script_path.replace('.m', '_result.json')

        # Add JSON output to the script
        full_script = script + f"\nsave('-text', '{result_json.replace(os.sep, '/')}', 'result');\nexit;\n"
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(full_script)

        try:
            env = os.environ.copy()
            env["PATH"] = os.path.dirname(self.octave_bin) + ";" + env.get("PATH", "")

            proc = subprocess.run(
                [self.octave_bin, "--no-gui", "--no-window-system", "--silent", script_path],
                capture_output=True, text=True, timeout=timeout,
                env=env, cwd=str(get_matpower_path())
            )

            if proc.returncode != 0:
                logger.error(f"Octave stderr: {proc.stderr[:500]}")
                return {"success": False, "error": proc.stderr[:500]}

            # Read the text output from Octave's stdout (JSON we printed)
            output = proc.stdout.strip()
            if not output:
                return {"success": False, "error": "No output from Octave"}

            # Try to extract JSON from output
            json_start = output.find('{')
            json_end = output.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = output[json_start:json_end]
                return json.loads(json_str)
            else:
                return {"success": False, "error": f"No JSON found in output: {output[:200]}"}

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Octave timeout"}
        except json.JSONDecodeError as e:
            return {"success": False, "error": f"JSON parse error: {e}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            for f in [script_path, result_json]:
                try:
                    os.unlink(f)
                except:
                    pass

    def _run_octave_json(self, script: str, timeout: int = 120) -> Dict[str, Any]:
        """
        Run Octave script that outputs JSON via printf to stdout.
        """
        with tempfile.NamedTemporaryFile(mode='w', suffix='.m', delete=False, encoding='utf-8') as f:
            f.write(script)
            script_path = f.name

        try:
            env = os.environ.copy()
            env["PATH"] = os.path.dirname(self.octave_bin) + ";" + env.get("PATH", "")

            proc = subprocess.run(
                [self.octave_bin, "--no-gui", "--no-window-system", "--silent", script_path],
                capture_output=True, text=True, timeout=timeout,
                env=env, cwd=str(get_matpower_path())
            )

            if proc.returncode != 0:
                logger.error(f"Octave error: {proc.stderr[:500]}")
                return {"success": False, "error": proc.stderr[:500]}

            output = proc.stdout.strip()
            if not output:
                return {"success": False, "error": "No output from Octave"}

            # Extract JSON from stdout
            json_start = output.find('{')
            json_end = output.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = output[json_start:json_end]
                return json.loads(json_str)

            # Try array JSON
            json_start = output.find('[')
            json_end = output.rfind(']') + 1
            if json_start >= 0 and json_end > json_start:
                return json.loads(output[json_start:json_end])

            return {"success": False, "error": f"No JSON in output: {output[:200]}"}

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Octave timeout"}
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            try:
                os.unlink(script_path)
            except:
                pass

    def _matrix_to_list(self, matrix) -> List[Dict[str, Any]]:
        """Convert a matrix (list of lists) to list of dicts using column maps."""
        if not matrix:
            return []
        return matrix

    # Cases suitable for web demo (avoid loading very large systems)
    WEB_DEMO_CASES = [
        'case4gs', 'case5', 'case6ww', 'case9', 'case9Q',
        'case14', 'case24_ieee_rts', 'case30', 'case30Q',
        'case39', 'case57', 'case118'
    ]

    def list_cases(self) -> List[Dict[str, Any]]:
        """Scan MATPOWER data directory for case files and parse metadata"""
        cases = []
        data_path = get_data_path()

        try:
            case_files = sorted(data_path.glob("case*.m"))
            for case_file in case_files:
                case_name = case_file.stem
                metadata = self._parse_case_metadata(case_file)
                metadata['name'] = case_name
                metadata['is_demo'] = case_name in self.WEB_DEMO_CASES
                cases.append(metadata)
        except Exception as e:
            logger.error(f"Error listing cases: {e}")

        return cases

    def _parse_case_metadata(self, case_file: Path) -> Dict[str, Any]:
        """
        Parse metadata from a MATPOWER .m case file without running Octave.

        Extracts bus/gen/branch row counts, baseMVA, and description comment.
        """
        result = {
            'buses': 0,
            'generators': 0,
            'branches': 0,
            'base_mva': 100.0,
            'description': '',
        }

        try:
            content = case_file.read_text(encoding='utf-8', errors='replace')
        except Exception as e:
            logger.warning(f"Could not read case file {case_file}: {e}")
            return result

        # Extract description: first non-empty comment line after function line
        desc_match = re.search(r'^%\s*(.+)$', content, re.MULTILINE)
        if desc_match:
            result['description'] = desc_match.group(1).strip()

        # Extract baseMVA
        basemva_match = re.search(r'mpc\.baseMVA\s*=\s*([\d.]+)', content)
        if basemva_match:
            result['base_mva'] = float(basemva_match.group(1))

        # Extract matrix row counts using regex with DOTALL to handle
        # matrices spanning multiple lines
        matrix_patterns = {
            'buses': r'mpc\.bus\s*=\s*\[(.*?)\]\s*;',
            'generators': r'mpc\.gen\s*=\s*\[(.*?)\]\s*;',
            'branches': r'mpc\.branch\s*=\s*\[(.*?)\]\s*;',
        }

        for key, pattern in matrix_patterns.items():
            match = re.search(pattern, content, re.DOTALL)
            if match:
                matrix_body = match.group(1)
                # Strip comment-only lines, then count rows by semicolons
                # (each data row ends with ;)
                lines = matrix_body.split('\n')
                count = 0
                for line in lines:
                    stripped = line.strip()
                    # Skip empty lines and comment-only lines
                    if not stripped or stripped.startswith('%'):
                        continue
                    # Count semicolons in data lines
                    count += stripped.count(';')
                result[key] = count

        return result

    def _matpower_header(self) -> str:
        """Generate Octave header to add MATPOWER paths"""
        return f"""
addpath('{self.matpower_path}');
addpath('{self.matpower_path}/lib');
addpath('{self.matpower_path}/data');
addpath('{self.matpower_path}/extras/misc');
addpath('{self.matpower_path}/extras/smartmarket');
addpath('{self.matpower_path}/mptest/lib');
addpath('{self.matpower_path}/mips/lib');
addpath('{self.matpower_path}/mp-opt-model/lib');
"""

    def load_case(self, case_name: str) -> Optional[Dict[str, Any]]:
        """Load a MATPOWER case file and return as Python dict"""
        if not self.is_initialized:
            return None

        case_path = f"{self.data_path}/{case_name}"
        script = self._matpower_header() + f"""
mpc = loadcase('{case_path}');
printf('{{');
printf('"base_mva": %f', mpc.baseMVA);

% Bus data
printf(', "bus": [');
for i = 1:size(mpc.bus, 1)
  if i > 1, printf(','); endif
  printf('[');
  for j = 1:size(mpc.bus, 2)
    if j > 1, printf(','); endif
    printf('%.6f', mpc.bus(i,j));
  endfor
  printf(']');
endfor
printf(']');

% Gen data
printf(', "gen": [');
for i = 1:size(mpc.gen, 1)
  if i > 1, printf(','); endif
  printf('[');
  for j = 1:size(mpc.gen, 2)
    if j > 1, printf(','); endif
    printf('%.6f', mpc.gen(i,j));
  endfor
  printf(']');
endfor
printf(']');

% Branch data
printf(', "branch": [');
for i = 1:size(mpc.branch, 1)
  if i > 1, printf(','); endif
  printf('[');
  for j = 1:size(mpc.branch, 2)
    if j > 1, printf(','); endif
    printf('%.6f', mpc.branch(i,j));
  endfor
  printf(']');
endfor
printf(']');

% Gencost
if isfield(mpc, 'gencost')
  printf(', "gencost": [');
  for i = 1:size(mpc.gencost, 1)
    if i > 1, printf(','); endif
    printf('[');
    for j = 1:size(mpc.gencost, 2)
      if j > 1, printf(','); endif
      printf('%.6f', mpc.gencost(i,j));
    endfor
    printf(']');
  endfor
  printf(']');
endif

printf('}}');
exit;
"""
        result = self._run_octave_json(script)
        if "error" in result and "base_mva" not in result:
            logger.error(f"Failed to load case: {result.get('error')}")
            return None

        # Convert matrices to named dicts
        bus_list = self._parse_matrix(result.get('bus', []), self.BUS_COLUMNS)
        gen_list = self._parse_matrix(result.get('gen', []), self.GEN_COLUMNS)
        branch_list = self._parse_matrix(result.get('branch', []), self.BRANCH_COLUMNS)

        return {
            'base_mva': result.get('base_mva', 100.0),
            'bus': bus_list,
            'gen': gen_list,
            'branch': branch_list,
            'gencost': result.get('gencost', None)
        }

    def _parse_matrix(self, matrix: List[List[float]], col_map: Dict[str, int]) -> List[Dict[str, Any]]:
        """Parse raw matrix rows into list of named dicts"""
        result = []
        for row in matrix:
            item = {}
            for name, idx in col_map.items():
                if idx < len(row):
                    val = row[idx]
                    if isinstance(val, float) and val == int(val) and abs(val) < 1e9:
                        item[name] = int(val) if name in ('bus_i', 'bus_type', 'gen_bus',
                            'gen_status', 'f_bus', 't_bus', 'br_status', 'area', 'zone',
                            'mbase') else val
                    else:
                        item[name] = val
                else:
                    item[name] = 0
            result.append(item)
        return result

    def _build_matrix_assignment(self, name: str, data_list: List[Dict[str, Any]],
                                  col_map: Dict[str, int], max_col: int) -> str:
        """Build Octave matrix assignment code from list of dicts"""
        lines = [f"{name} = ["]
        for item in data_list:
            row = [0.0] * max_col
            for field, idx in col_map.items():
                if field in item and idx < max_col:
                    row[idx] = float(item[field])
            lines.append("  " + " ".join(f"{v}" for v in row) + ";")
        lines.append("];")
        return "\n".join(lines)

    def run_power_flow(self, case_data: Dict[str, Any], algorithm: str = 'NR') -> Dict[str, Any]:
        """Run AC power flow via Octave subprocess"""
        if not self.is_initialized:
            return {"success": False, "error": "Octave not initialized"}

        start_time = time.time()

        # Build Octave script
        bus_code = self._build_matrix_assignment("mpc.bus", case_data['bus'],
                                                  self.BUS_COLUMNS, 13)
        gen_code = self._build_matrix_assignment("mpc.gen", case_data['gen'],
                                                  self.GEN_COLUMNS, min(21, max(
                                                      max(self.GEN_COLUMNS.values()) + 1,
                                                      len(case_data['gen'][0]) if case_data['gen'] else 1)))
        branch_code = self._build_matrix_assignment("mpc.branch", case_data['branch'],
                                                     self.BRANCH_COLUMNS, 13)

        header = self._matpower_header()
        script = header + f"""
mpc.version = '2';
mpc.baseMVA = {case_data.get('base_mva', 100.0)};
{bus_code}
{gen_code}
{branch_code}

mpopt = mpoption('verbose', 0, 'out.all', 0);
results = runpf(mpc, mpopt);

printf('{{');
printf('"success": %d', results.success);
printf(', "iterations": %d', 0);

% Bus results
printf(', "bus": [');
for i = 1:size(results.bus, 1)
  if i > 1, printf(','); endif
  printf('[');
  for j = 1:size(results.bus, 2)
    if j > 1, printf(','); endif
    printf('%.6f', results.bus(i,j));
  endfor
  printf(']');
endfor
printf(']');

% Gen results
printf(', "gen": [');
for i = 1:size(results.gen, 1)
  if i > 1, printf(','); endif
  printf('[');
  for j = 1:size(results.gen, 2)
    if j > 1, printf(','); endif
    printf('%.6f', results.gen(i,j));
  endfor
  printf(']');
endfor
printf(']');

% Branch results
printf(', "branch": [');
for i = 1:size(results.branch, 1)
  if i > 1, printf(','); endif
  printf('[');
  for j = 1:size(results.branch, 2)
    if j > 1, printf(','); endif
    printf('%.6f', results.branch(i,j));
  endfor
  printf(']');
endfor
printf(']');

printf('}}');
exit;
"""
        result = self._run_octave_json(script, timeout=settings.OCTAVE_TIMEOUT)

        if "error" in result and "success" not in result:
            return {"success": False, "error": result["error"], "et": time.time() - start_time}

        bus_results = self._parse_matrix(result.get('bus', []), self.BUS_COLUMNS)
        gen_results = self._parse_matrix(result.get('gen', []), self.GEN_COLUMNS)
        branch_results = self._parse_matrix(result.get('branch', []), self.BRANCH_COLUMNS)

        return {
            'success': bool(result.get('success', 0)),
            'iterations': result.get('iterations', 0),
            'et': time.time() - start_time,
            'bus_results': bus_results,
            'gen_results': gen_results,
            'branch_results': branch_results
        }

    def run_dc_power_flow(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run DC power flow"""
        if not self.is_initialized:
            return {"success": False, "error": "Octave not initialized"}

        start_time = time.time()

        bus_code = self._build_matrix_assignment("mpc.bus", case_data['bus'],
                                                  self.BUS_COLUMNS, 13)
        gen_code = self._build_matrix_assignment("mpc.gen", case_data['gen'],
                                                  self.GEN_COLUMNS, min(21, max(
                                                      max(self.GEN_COLUMNS.values()) + 1,
                                                      len(case_data['gen'][0]) if case_data['gen'] else 1)))
        branch_code = self._build_matrix_assignment("mpc.branch", case_data['branch'],
                                                     self.BRANCH_COLUMNS, 13)

        script = self._matpower_header() + f"""
mpc.version = '2';
mpc.baseMVA = {case_data.get('base_mva', 100.0)};
{bus_code}
{gen_code}
{branch_code}

mpopt = mpoption('verbose', 0, 'out.all', 0);
mpopt = mpoption(mpopt, 'pf.dc', 1);
results = runpf(mpc, mpopt);

printf('{{');
printf('"success": %d', results.success);

printf(', "bus": [');
for i = 1:size(results.bus, 1)
  if i > 1, printf(','); endif
  printf('[');
  for j = 1:size(results.bus, 2)
    if j > 1, printf(','); endif
    printf('%.6f', results.bus(i,j));
  endfor
  printf(']');
endfor
printf(']');

printf(', "gen": [');
for i = 1:size(results.gen, 1)
  if i > 1, printf(','); endif
  printf('[');
  for j = 1:size(results.gen, 2)
    if j > 1, printf(','); endif
    printf('%.6f', results.gen(i,j));
  endfor
  printf(']');
endfor
printf(']');

printf(', "branch": [');
for i = 1:size(results.branch, 1)
  if i > 1, printf(','); endif
  printf('[');
  for j = 1:size(results.branch, 2)
    if j > 1, printf(','); endif
    printf('%.6f', results.branch(i,j));
  endfor
  printf(']');
endfor
printf(']');

printf('}}');
exit;
"""
        result = self._run_octave_json(script, timeout=settings.OCTAVE_TIMEOUT)

        if "error" in result and "success" not in result:
            return {"success": False, "error": result["error"], "et": time.time() - start_time}

        bus_results = self._parse_matrix(result.get('bus', []), self.BUS_COLUMNS)
        gen_results = self._parse_matrix(result.get('gen', []), self.GEN_COLUMNS)
        branch_results = self._parse_matrix(result.get('branch', []), self.BRANCH_COLUMNS)

        return {
            'success': bool(result.get('success', 0)),
            'iterations': 0,
            'et': time.time() - start_time,
            'bus_results': bus_results,
            'gen_results': gen_results,
            'branch_results': branch_results
        }

    def run_opf(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run Optimal Power Flow"""
        if not self.is_initialized:
            return {"success": False, "error": "Octave not initialized"}

        start_time = time.time()

        bus_code = self._build_matrix_assignment("mpc.bus", case_data['bus'],
                                                  self.BUS_COLUMNS, 13)
        gen_code = self._build_matrix_assignment("mpc.gen", case_data['gen'],
                                                  self.GEN_COLUMNS, min(21, max(
                                                      max(self.GEN_COLUMNS.values()) + 1,
                                                      len(case_data['gen'][0]) if case_data['gen'] else 1)))
        branch_code = self._build_matrix_assignment("mpc.branch", case_data['branch'],
                                                     self.BRANCH_COLUMNS, 13)

        gencost_code = ""
        if case_data.get('gencost'):
            gencost = case_data['gencost']
            gencost_code = "mpc.gencost = [\n"
            for row in gencost:
                gencost_code += "  " + " ".join(str(float(v)) for v in row) + ";\n"
            gencost_code += "];\n"

        script = self._matpower_header() + f"""
mpc.version = '2';
mpc.baseMVA = {case_data.get('base_mva', 100.0)};
{bus_code}
{gen_code}
{branch_code}
{gencost_code}

mpopt = mpoption('verbose', 0, 'out.all', 0);
results = runopf(mpc, mpopt);

printf('{{');
printf('"success": %d', results.success);
printf(', "iterations": %d', 0);

try
  printf(', "total_cost": %.6f', results.f);
catch
  printf(', "total_cost": 0');
end_try_catch

printf(', "bus": [');
for i = 1:size(results.bus, 1)
  if i > 1, printf(','); endif
  printf('[');
  for j = 1:size(results.bus, 2)
    if j > 1, printf(','); endif
    printf('%.6f', results.bus(i,j));
  endfor
  printf(']');
endfor
printf(']');

printf(', "gen": [');
for i = 1:size(results.gen, 1)
  if i > 1, printf(','); endif
  printf('[');
  for j = 1:size(results.gen, 2)
    if j > 1, printf(','); endif
    printf('%.6f', results.gen(i,j));
  endfor
  printf(']');
endfor
printf(']');

printf(', "branch": [');
for i = 1:size(results.branch, 1)
  if i > 1, printf(','); endif
  printf('[');
  for j = 1:size(results.branch, 2)
    if j > 1, printf(','); endif
    printf('%.6f', results.branch(i,j));
  endfor
  printf(']');
endfor
printf(']');

printf('}}');
exit;
"""
        result = self._run_octave_json(script, timeout=settings.OCTAVE_TIMEOUT * 2)

        if "error" in result and "success" not in result:
            return {"success": False, "error": result["error"], "et": time.time() - start_time}

        bus_results = self._parse_matrix(result.get('bus', []), self.BUS_COLUMNS)
        gen_results = self._parse_matrix(result.get('gen', []), self.GEN_COLUMNS)
        branch_results = self._parse_matrix(result.get('branch', []), self.BRANCH_COLUMNS)

        return {
            'success': bool(result.get('success', 0)),
            'iterations': result.get('iterations', 0),
            'et': time.time() - start_time,
            'bus_results': bus_results,
            'gen_results': gen_results,
            'branch_results': branch_results,
            'total_cost': result.get('total_cost', 0.0)
        }

    def apply_modifications(self, case_data: Dict[str, Any], modifications: Dict[str, Any]) -> Dict[str, Any]:
        """Apply modifications to case data (in-memory)"""
        modified = copy.deepcopy(case_data)

        for mod_type, mod_list in modifications.items():
            if mod_type == 'outages':
                # Handle outage-style modifications: {'generators': [idx, ...], 'branches': [idx, ...]}
                if not isinstance(mod_list, dict):
                    continue
                for gen_idx in mod_list.get('generators', []):
                    if gen_idx is not None and 0 <= gen_idx < len(modified['gen']):
                        modified['gen'][gen_idx]['gen_status'] = 0
                        modified['gen'][gen_idx]['pg'] = 0
                        modified['gen'][gen_idx]['qg'] = 0
                for br_idx in mod_list.get('branches', []):
                    if br_idx is not None and 0 <= br_idx < len(modified['branch']):
                        modified['branch'][br_idx]['br_status'] = 0
            elif mod_type == 'bus':
                for mod in mod_list:
                    idx = mod.get('index')
                    field = mod.get('field')
                    value = mod.get('value')
                    if idx is None or field is None:
                        continue
                    if 0 <= idx < len(modified['bus']):
                        modified['bus'][idx][field] = value
            elif mod_type == 'gen':
                for mod in mod_list:
                    idx = mod.get('index')
                    field = mod.get('field')
                    value = mod.get('value')
                    if idx is None or field is None:
                        continue
                    if 0 <= idx < len(modified['gen']):
                        modified['gen'][idx][field] = value
            elif mod_type == 'branch':
                for mod in mod_list:
                    idx = mod.get('index')
                    field = mod.get('field')
                    value = mod.get('value')
                    if idx is None or field is None:
                        continue
                    if 0 <= idx < len(modified['branch']):
                        modified['branch'][idx][field] = value

        return modified

    def cleanup(self):
        """No-op for subprocess engine"""
        self.is_initialized = False


# Global engine instance
_engine_instance: Optional[OctaveEngine] = None


def get_engine() -> OctaveEngine:
    """Get or create the global Octave engine instance"""
    global _engine_instance
    if _engine_instance is None or not _engine_instance.is_initialized:
        _engine_instance = OctaveEngine()
    return _engine_instance


def cleanup_engine():
    """Cleanup the global engine instance"""
    global _engine_instance
    if _engine_instance:
        _engine_instance.cleanup()
        _engine_instance = None
