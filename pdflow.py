#!/usr/bin/env python3
import os
import sys
import stat
import re
import argparse
import logging
from typing import Tuple, Union, List

'''
###################################
# NEED TO LOAD CUSTOM PACKAGES AFTER SETTING UP OVDIR
###################################
from flow_utils import *

# top-level binary should initialize flow_cfg at the very first as it can be used in pdflow and ldflow
import flow_env_utils
flow_env_utils.init()
from flow_env_utils import flow_envs as FLOW_ENVS

import flow_config_utils
flow_config_utils.init()
from flow_config_utils import flow_cfgs as FLOW_CFGS

import flow_var_utils
flow_var_utils.init()
from flow_var_utils import flow_vars as FLOW_VARS

import flow_log_utils
import flow_args_utils
import flow_file_utils
import flow_git_utils

import project
import set_ce_ovdir
import pdflow_syn
import pdflow_pnr
import pdflow_ext
import pdflow_sta
import pdflow_emir
'''

__author__ = 'Kyungwook Chang'

parser = argparse.ArgumentParser(description='DAL physical design flow. you need to setup project (using setup_project) before using it (other than \'common\' project)')
parser.add_argument('-ovdir', action='store', type=str, metavar='<directory>', help='override directory. path to the directory which patch scripts exist')
parser.add_argument('-setvar', action='append', type=str, metavar='"FLOW_VAR=VALUE"', help='set a flow variable. this has the highest priority, and will override flow vars settings in vars_setup.py. need to enclosed in double quotes. you can use this option multiple times.')
parser.add_argument('-debug', action='store_true', help='run this flow in debug mode')
subparsers = parser.add_subparsers(help='available sub-commands', dest='command')

add_block_parser_epilog = '''
<example>
assume the below is defined in 'DESIGN':'HIER' of design.config 
aes_128: {
    Round: {}
    SubBytes {}
    ShiftRows {}
    AddRoundKey {}
}
in here,
    - design = aes_128
    - block = Round, SubBytes, ShiftRows, AddRoundKey

<rule>
- blocks are basic units of hierarchy
    e.g.#1> if you want to implement Round with sub-designs in an handoff directory,
        % pdflow add_block -tech <tech_name> -design aes_128 -block Round 
- if a block is defined under a design, the block can be reused in the design.
- if a design has multiple blocks in it, but you want to flatten it, use -flat option
    e.g.#2> if you want aes_128 to be flat,
        % pdflow add_block -tech <tech_name> -design aes_128 -flat
'''
add_block_parser = subparsers.add_parser('add_block', help='add a block to be implemented in the project environment. this command should be performed in an project environment (pe)', epilog=add_block_parser_epilog, formatter_class=argparse.RawDescriptionHelpFormatter)
add_block_parser.add_argument('-tech', action='store', type=str, metavar='<process>[/<version>]', help='process node used for implementation. check "pdflow.py list_tech" for available process nodes. format: <process> for the latest version, <process>/<version> for specific version. e.g., to use /dal/tech/NANGATE45/2020_10, -tech NANGATE45/2020_10', required=True)
add_block_parser.add_argument('-design', action='store', type=str, metavar='<design_name>', help='design to be implemented. check "pdflow.py list_design" for available designs. format: <design>. e.g., to use /dal/designs/aes_128, -design aes_128', required=True)
add_block_parser.add_argument('-block', action='store', type=str, metavar='<block_name>', help='implement only block in a design. to check the hierarchy, see design.config')
add_block_parser.add_argument('-flat', action='store_true', help='flattens all sub-hierarchy of the specified block')

create_wa_parser = subparsers.add_parser('create_wa', help='create a workarea to perform physical design. this command should be performed in block directory (\'impl\' directory of a project environment')
create_wa_parser.add_argument('-name', action='store', type=str, help='name of the workarea. this will become directory name.', required=True)
create_wa_parser.add_argument('-handoff_id', action='store', type=str, help='handoff ID under the handoff directory of the project, from which the sub-hierarhcy designs are being used')
supported_impl_type = ['2d', 'f2b', 'f2f']
create_wa_parser.add_argument('-impl_type', action='store', type=str, choices=supported_impl_type, default='2d', help='implementation type of the design (2d, f2b(3d), f2f(3d))')
supported_impl_method = ['compact2d']
create_wa_parser.add_argument('-impl_method', action='store', type=str, choices=supported_impl_method, default='compact2d', help='method used to implement 3d design. meaningful only when -impl_type is f2b or f2f')

clone_wa_parser = subparsers.add_parser('clone_wa', help='clone a workarea with the same project environment. this command should be performed in block directory (\'impl\' directory of a project environment)')
clone_wa_parser.add_argument('-src', action='store', type=str, metavar='<src_wa>', help='directory path to the source workarea', required=True)
clone_wa_parser.add_argument('-dest', action='store', type=str, metavar='<wa_name>', help='name of the cloned workarea', required=True)
clone_wa_parser.add_argument('-flow', action='store', type=str, nargs='+', help='specify the flow to be cloned. you can specify multiple flows. if not specified, it will clone every flows. e.g., -flow pnr sta')
clone_wa_parser.add_argument('-stage', action='store', type=str, nargs='+', help='specify the stage to be cloned. you can specify multiple stages. if not specified, it will clone every stages. e.g., -stage cts finish')
clone_wa_parser.add_argument('-aslink', action='store_true', help='all the cloned files are created as symbolic links')

handoff_parser = subparsers.add_parser('handoff', help='handoff the current workarea. this command should be performed in a workarea')
handoff_parser.add_argument('-handoff_id', action='store', type=str, help='handoff the block of the current workarea in the handoff directory of the project with the specified handoff id', required=True)

update_interface_parser = subparsers.add_parser('update_interface', help='update interface design. this command should be performed in a workarea')
update_interface_parser.add_argument('-handoff_id', action='store', type=str, help='update the handoff id of the sub-hierarchy designs', required=True)
update_interface_parser.add_argument('-block', action='store', metavar='<block_name>', type=str, help='limit the update to the block')

history_parser = subparsers.add_parser('history', help='show command history of the current workarea. by default, show only the last 10 history. this command should be performed in a workarea')
history_parser.add_argument('-all', action='store_true', help='show all history')
history_parser.add_argument('-num', action='store', type=int, metavar='<num>', help='show only the last <num> history')

list_tech_parser = subparsers.add_parser('list_tech', help='show available process nodes')
list_design_parser = subparsers.add_parser('list_design', help='show available designs')

supported_flows = ['syn', 'pnr', 'ext', 'sta', 'emir', 'sim']

syn_parser = subparsers.add_parser('syn', help='perform logic synthesis of the current design')
supported_syn_tools = ['dc']
syn_parser.add_argument('-tool', action='store', type=str, choices=supported_syn_tools, default=supported_syn_tools[0], help='tool to use for synthesis')
syn_parser.add_argument('-tool_version', action='store', type=str, help='tool version to use for synthesis. e.g.: O-2018.06-SP4')
syn_parser.add_argument('-clean_prevrun', action='store_true', help='delete the existing runs')
supported_syn_runs = ['setup', 'run', 'main', 'postproc', 'interactive']
syn_parser.add_argument('-run', action='store', type=str, choices=supported_syn_runs, default='main', help='phase to run in the flow. setup: make scripts only, run: run the tool and perform postproc (skip making scripts), postproc: perform postproc (skip making scripts and running tool), interactive: open GUI for existing runs')

pnr_parser = subparsers.add_parser('pnr', help='perform pnr of the current designs', formatter_class=argparse.RawTextHelpFormatter)
supported_pnr_stages = ['init', 'floorplan', 'place', 'cts', 'postcts_opt', 'route', 'postroute_opt', 'finish', '3d_partition', '3d_legalize', '3d_route', '3d_split', '3d_trial', '3d_opt', '3d_finish', '3d_merge']
supported_pnr_2d_stages = ['init', 'floorplan', 'place', 'cts', 'postcts_opt', 'route', 'postroute_opt', 'finish']
supported_pnr_3d_stages = ['init', 'floorplan', 'place', 'cts', 'postcts_opt', 'route', 'postroute_opt', 'finish', '3d_partition', '3d_legalize', '3d_route', '3d_split', '3d_trial', '3d_opt', '3d_finish', '3d_merge']
pnr_parser_stage_help = '''pnr stage to perform. it will perform all the stages prior to the specified stage if required. if not specified, it will perform all the stages.
supported stages
- WA_CFG[IMPL_TYPE]=2d: %s
- WA_CFG[IMPL_TYPE]=f2b or f2f: %s
''' % (','.join(supported_pnr_2d_stages), ', '.join(supported_pnr_3d_stages))
pnr_parser.add_argument('-stage', action='store', type=str, choices=supported_pnr_stages, help=pnr_parser_stage_help)
supported_pnr_tools = ['innovus']
pnr_parser.add_argument('-tool', action='store', type=str, choices=supported_pnr_tools, default=supported_pnr_tools[0], help='tool to use for pnr')
pnr_parser.add_argument('-tool_version', action='store', type=str, help='tool version to use for pnr. e.g.: 19.11')
pnr_parser.add_argument('-clean_prevrun', action='store_true', help='delete existing run')
supported_pnr_runs = ['setup', 'run', 'main', 'postproc', 'interactive']
pnr_parser.add_argument('-run', action='store', type=str, choices=supported_pnr_runs, default='main', help='phase to run in the flow. setup: make scripts only, run: run the tool and perform postproc (skip making scripts), postproc: perform postproc (skip making scripts and running tool), interactive: open GUI for existing runs')
pnr_parser.add_argument('-design', action='store', type=str, help='choose design to open in interactive runs (typically used for 3d designs "part0" or "part1") (if not given, it will open the main design)')

ext_parser = subparsers.add_parser('ext', help='perform parasitic extraction of designs')
supported_ext_stages = ['route', 'postroute_opt', 'finish', '3d_route', '3d_finish']
ext_parser.add_argument('-stage', action='store', type=str, choices=supported_ext_stages, help='pnr stage to perform extraction. if not specified, finish stage will be use for 2d designs, 3d_route stage for compact2d 3d designs, and 3d_finish stage for shrunk2d 3d designs')
ext_parser.add_argument('-corner', action='store', type=str, nargs='+', help='specify corners to perform ext. you can specify multiple corners. if not given, it will perform extraction for all the corners in TECH_CFG:EXT:CORNERS in tech.config file. -corner slow fast')
supported_ext_tools = ['starrc']
ext_parser.add_argument('-tool', action='store', type=str, choices=supported_ext_tools, default=supported_ext_tools[0], help='tool to use for extraction')
ext_parser.add_argument('-tool_version', action='store', type=str, help='tool version to use for extraction')
ext_parser.add_argument('-clean_prevrun', action='store_true', help='delete existing run')
supported_ext_runs = ['setup', 'run', 'main', 'postproc']
ext_parser.add_argument('-run', action='store', type=str, choices=supported_ext_runs, default='main', help='phase to run in the flow. setup: make scripts only, run: run the tool and perform postproc (skip making scripts), postproc: perform postproc (skip making scripts and running tool), interactive: open GUI for existing runs')

sta_parser = subparsers.add_parser('sta', help='perform timing and power analysis of designs')
supported_sta_stages = ['route', 'postroute_opt', 'finish', '3d_route', '3d_finish']
sta_parser.add_argument('-stage', action='store', type=str, choices=supported_sta_stages, help='pnr stage to perform sta. if not specified, finish stage will be use for 2d designs, 3d_route stage for compact2d 3d designs, and 3d_finish stage for shrunk2d 3d designs')
sta_parser.add_argument('-corner', action='store', type=str, nargs='+', help='specify corners to perform sta. you can specify multiple corners. if not given, it will perform extraction for all the corners in TECH_CFG:STA:CORNERS in tech.config file. -corner slow fast')
supported_sta_tools = ['pt', 'tempus']
sta_parser.add_argument('-tool', action='store', type=str, choices=supported_sta_tools, default=supported_sta_tools[0], help='tool to use for sta')
sta_parser.add_argument('-tool_version', action='store', type=str, help='tool version to use for sta')
sta_parser.add_argument('-clean_prevrun', action='store_true', help='delete existing run')
supported_sta_runs = ['setup', 'run', 'main', 'postproc', 'interactive']
sta_parser.add_argument('-run', action='store', type=str, choices=supported_sta_runs, default='main', help='phase to run in the flow. setup: make scripts only, run: run the tool and perform postproc (skip making scripts), postproc: perform postproc (skip making scripts and running tool), interactive: open GUI for existing runs')

emir_parser = subparsers.add_parser('emir', help='perform power rail analysis of designs')
supported_emir_stages = ['route', 'postroute_opt', 'finish', '3d_route', '3d_finish']
emir_parser.add_argument('-stage', action='store', type=str, choices=supported_emir_stages, help='pnr stage to perform power rail analysis. if not specified, finish stage will be use for 2d designs, 3d_route stage for compact2d 3d designs, and 3d_finish stage for shrunk2d 3d designs')
# the current Ansys license does not support signalEM
#supported_emir_modes = ['static', 'dynamic', 'vector', 'signalEM']
supported_emir_modes = ['static', 'dynamic', 'vector']
emir_parser.add_argument('-mode', action='store', type=str, choices=supported_emir_modes, required=True, help='rail analysis mode')
supported_emir_tools = ['redhawk', 'voltus']
emir_parser.add_argument('-tool', action='store', type=str, choices=supported_emir_tools, default=supported_emir_tools[0], help='tool to use for rail analysis')
emir_parser.add_argument('-tool_version', action='store', type=str, help='tool version to use for rail analysis')
emir_parser.add_argument('-clean_prevrun', action='store_true', help='delete existing run')
#supported_emir_runs = ['setup', 'twf', 'pgv', 'run', 'main', 'postproc', 'interactive']
supported_emir_runs = ['setup', 'pgv', 'run', 'main', 'postproc', 'interactive']
emir_parser.add_argument('-run', action='store', type=str, choices=supported_emir_runs, default='main', help='phase to run in the flow. setup: make scripts only, run: run the tool and perform postproc (skip making scripts), postproc: perform postproc (skip making scripts and running tool), interactive: open GUI for existing runs')

sim_parser = subparsers.add_parser('sim', help='simulate the current design with a testbench')
supported_sim_tools = ['vcs']
supported_sim_target_flows = ['fe', 'syn', 'pnr']
sim_parser.add_argument('-target_flow', action='store', type=str, choices=supported_sim_target_flows, help='target flow to run simulation')
sim_parser.add_argument('-stage', action='store', type=str, choices=supported_pnr_stages, help='pnr stage to run simulation (set only when -target_flow is pnr)')
sim_parser.add_argument('-tool', action='store', type=str, choices=supported_sim_tools, default=supported_sim_tools[0], help='tool to use for simulation')
sim_parser.add_argument('-tool_version', action='store', type=str, help='tool version to use for simulation. e.g.: O-2018.06-SP4')
sim_parser.add_argument('-clean_prevrun', action='store_true', help='delete the existing runs')
supported_sim_runs = ['setup', 'run', 'main', 'postproc', 'interactive']
sim_parser.add_argument('-run', action='store', type=str, choices=supported_sim_runs, default='main', help='phase to run in the flow. setup: make scripts only, run: run the tool and perform postproc (skip making scripts), postproc: perform postproc (skip making scripts and running tool), interactive: open GUI for existing runs')


############################################################
# PRIMITIVE FUNCTIONS
############################################################
def create_history(command: str, time: str, log_file: str):
    '''
    create a history file in history directory in the current workarea

    :param command: current pdflow command
    :param time: current time
    :param log_file: log file in log directory in the current workarea
    :return: None
    '''
    import flow_config_utils
    from flow_config_utils import flow_cfgs as FLOW_CFGS
    import flow_file_utils

    cur_dir = os.getcwd()

    wa_cfg_file = os.path.join(cur_dir, 'configs', 'wa.config')
    flow_config_utils.read_config(wa_cfg_file)

    history_file = os.path.join(cur_dir, 'history', flow_file_utils.join_filename('pdflow', time, 'cmd'))
    ofp = flow_file_utils.open_wfile(history_file)
    ofp.write('#!/bin/tcsh\n')
    ofp.write('# PROJECT = %s\n' % (FLOW_CFGS['WA_CFG']['PROJECT']))
    ofp.write('# BRANCH = %s\n' % (FLOW_CFGS['WA_CFG']['BRANCH']))
    ofp.write('# HOST = %s\n' % (FLOW_CFGS['HOST']))
    ofp.write('# USER = %s\n' % (FLOW_CFGS['USER']))
    ofp.write('# Created = %s\n' % (time))
    ofp.write('# CE_VERSION = %s\n' % (FLOW_CFGS['CE_VERSION']))
    ofp.write('# CE_DIR = %s\n' % (FLOW_CFGS['CE_DIR']))
    ofp.write('# WORK_AREA = %s\n' % (FLOW_CFGS['WA_CFG']['DIR']))
    ofp.write('# LOGFILE = %s\n' % (log_file))
    ofp.write('%s\n' % (command))
    ofp.close()
    os.chmod(history_file, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)

    latest_history_file = os.path.join(cur_dir, 'history', 'pdflow.latest.cmd')
    flow_file_utils.make_symlink(history_file, latest_history_file)


def read_pdflow_configs(flow: str, tool: str):
    '''
    read all config files related to the specified flow and tool in pdflow. the following config files are read. read configs are stored in FLOW_CFGS
    - $CE_DIR/configs/<flow>.config
    - $CE_DIR/configs/<tool>.config
    - $TECH_DIR/<process>/<version>/configs/tech.config
    - $DESIGN_DIR/<design_name>/configs/design.config
    - $DESIGN_DIR/<design_name>/configs/block.config
    <process>, <version> and <design> information is fetched from wa.config file

    :param flow: flow to read config
    :param tool: tool to read config
    :return: None
    '''
    from flow_env_utils import flow_envs as FLOW_ENVS
    import flow_config_utils

    cfg_files = [
        os.path.join(FLOW_ENVS['CE_DIR'], 'configs', flow + '.config'),
        os.path.join(FLOW_ENVS['CE_DIR'], 'configs', tool + '.config'),
        os.path.join(os.getenv('TECH_DIR'), FLOW_ENVS['TECH'], 'configs', 'tech.config'),
        os.path.join(os.getenv('DESIGN_DIR'), FLOW_ENVS['DESIGN'], 'configs', 'design.config'),
        os.path.join(os.getenv('DESIGN_DIR'), FLOW_ENVS['DESIGN'], 'configs', 'block.config'),
    ]
    for cfg_file in cfg_files:
        if os.path.exists(cfg_file):
            flow_config_utils.read_config(cfg_file)


def read_pdflow_vars_specs(flow: str):
    '''
    read all vars_spec.py files related to the specified flow in pdflow. the following vars_spec.py files are read. read vars_spec are stored in FLOW_VARS
    - $CE_DIR/pdflow/common/vars_spec.py (lowest priority)
    - $CE_DIR/pdflow/<flow>/vars_spec.py
    - $CE_OVDIR/vars_spec.py if ovdir is given (highest priority)

    :param flow: flow to read vars_spec.py
    :return: None
    '''
    from flow_env_utils import flow_envs as FLOW_ENVS
    import flow_var_utils

    ce_dir = os.path.join(FLOW_ENVS['CE_DIR'])
    vars_spec_files = [
        os.path.join(ce_dir, 'pdflow', 'common', 'vars_spec.py'),
        os.path.join(ce_dir, 'pdflow', flow, 'vars_spec.py'),
    ]
    if 'CE_OVDIR' in FLOW_ENVS:
        if os.path.exists(os.path.join(FLOW_ENVS['CE_OVDIR'], 'vars_spec.py')):
            import flow_log_utils
            logger = flow_log_utils.start_logging()
            logger.warning('vars_spec.py in ovdir %s detected. reading...' % (os.path.abspath(FLOW_ENVS['CE_OVDIR'])))
            vars_spec_files.append(os.path.join(FLOW_ENVS['CE_OVDIR'], 'vars_spec.py'))

    for vars_spec_file in vars_spec_files:
        if os.path.exists(vars_spec_file):
            flow_var_utils.read_vars_spec(vars_spec_file)


def read_pdflow_vars_setups(flow: str):
    '''
    read all vars_setup.py files related to the specified flow in pdflow. the following vars_setup.py files are read. read vars_setup are stored in FLOW_VARS
    - $WA_DIR/scripts/pdflow/<design_name>/common/vars_setup.py (lowest priority)
    - $WA_DIR/scripts/pdflow/<design_name>/common/<flow>/vars_setup.py
    - $WA_DIR/scripts/pdflow/<design_name>/<process>/<version>/vars_setup.py
    - $WA_DIR/scripts/pdflow/<design_name>/<process>/<version>/<flow>/vars_setup.py
    - $WA_DIR/scripts/pdflow/<design_name>/<block_name>/common/vars_setup.py
    - $WA_DIR/scripts/pdflow/<design_name>/<block_name>/common/<flow>/vars_setup.py
    - $WA_DIR/scripts/pdflow/<design_name>/<block_name>/<process>/<version>/vars_setup.py
    - $WA_DIR/scripts/pdflow/<design_name>/<block_name>/<process>/<version>/<flow>/vars_setup.py (highest priority)

    :param flow: flow to read vars_spec.py
    :return: None
    '''
    from flow_env_utils import flow_envs as FLOW_ENVS
    import flow_var_utils

    proj_script_dir = os.path.join(FLOW_ENVS['WORK_AREA'], 'scripts', FLOW_ENVS['PROJECT'])
    vars_setup_files = [
        os.path.join(proj_script_dir, 'pdflow', FLOW_ENVS['DESIGN'], 'common', 'vars_setup.py'),
        os.path.join(proj_script_dir, 'pdflow', FLOW_ENVS['DESIGN'], 'common', flow, 'vars_setup.py'),
        os.path.join(proj_script_dir, 'pdflow', FLOW_ENVS['DESIGN'], FLOW_ENVS['TECH'], 'vars_setup.py'),
        os.path.join(proj_script_dir, 'pdflow', FLOW_ENVS['DESIGN'], FLOW_ENVS['TECH'], flow, 'vars_setup.py'),
        os.path.join(proj_script_dir, 'pdflow', FLOW_ENVS['DESIGN'], FLOW_ENVS['BLOCK'], 'common', 'vars_setup.py'),
        os.path.join(proj_script_dir, 'pdflow', FLOW_ENVS['DESIGN'], FLOW_ENVS['BLOCK'], 'common', flow, 'vars_setup.py'),
        os.path.join(proj_script_dir, 'pdflow', FLOW_ENVS['DESIGN'], FLOW_ENVS['BLOCK'], FLOW_ENVS['TECH'], 'vars_setup.py'),
        os.path.join(proj_script_dir, 'pdflow', FLOW_ENVS['DESIGN'], FLOW_ENVS['BLOCK'], FLOW_ENVS['TECH'], flow, 'vars_setup.py'),
    ]

    for vars_setup_file in vars_setup_files:
        if os.path.exists(vars_setup_file):
            flow_var_utils.read_vars_setup(vars_setup_file)

    for set_var_str in flow_var_utils.set_vars_from_cli:
        flow_var_utils.set_var_from_str(set_var_str)

    # check whether every mandatory vars are read
    flow_var_utils.check_vars()


def check_design(design: str, block: str):
    '''
    check whether the given block is part of the design. if it is not part of the design, it errors out

    :param design: design name
    :param block: block name
    :return: None
    '''
    from flow_config_utils import flow_cfgs as FLOW_CFGS
    import flow_log_utils

    logger = flow_log_utils.start_logging()

    if 'HIER' not in FLOW_CFGS['DESIGN_CFG']:
        logger.error('\'HIER\' is not defined in the design config')
        sys.exit()
    if design not in FLOW_CFGS['DESIGN_CFG']['HIER']:
        logger.error('design %s is not defined in \'HIER\' in the design config')
        sys.exit()
    if block is not None and block not in FLOW_CFGS['DESIGN_CFG']['HIER'][design]:
        logger.error('block %s is not defined in \'HIER\' in the design config')
        sys.exit()


def get_tech_version(tech_name: str) -> Tuple[str, str]:
    '''
    from string with both tech name and its version (e.g., NANGATE45/2020_10), get tech name (e.g., NANGATE45) and its version (2020_10)

    :param tech_name: string with both tech name and its version with delimiter '/'
    '''
    match = re.match(r'(?P<tech>\S+)/(?P<version>\S+)', tech_name)
    if match:
        tech = match.group('tech')
        version = match.group('version')
    else:
        tech = tech_name
        version = 'latest'
    return tech, version


def get_3d_layer_conf_name() -> str:
    '''
    return layer configuration name of 3D designs
    (e.g., m4bm6t: 4 layers in bottom tier (part0), 6 layers in top tier (part1))

    :return: layer configuration name
    '''
    from flow_var_utils import flow_vars as FLOW_VARS

    return 'm' + str(FLOW_VARS['PNR_3D_NUM_ROUTE_LAYERS'][0]) + 'b' + 'm' + str(FLOW_VARS['PNR_3D_NUM_ROUTE_LAYERS'][1]) + 't'


def list_available_tech():
    '''
    print available technology nodes in pdflow
    '''
    option_header = ['TECH', 'VERSION', 'LATEST']
    import re
    import flow_log_utils
    import flow_args_utils

    logger = flow_log_utils.start_logging()

    tech_dir = os.environ['TECH_DIR']
    tech_list = []
    hidden_dir = re.compile('^\\.')
    for entry in os.listdir(tech_dir):
        if os.path.isfile(os.path.join(tech_dir, entry)) or re.match(hidden_dir, entry) is not None:  # if it is file or dir which is started with '.', ignore it
            continue
        else:
            tech_list.append(entry)
    tech_version_dict = {}
    for each_tech in tech_list:
        tech_version_dir = os.path.join(tech_dir, each_tech)
        tech_version_list = []
        already_write = []
        for each_version in os.listdir(tech_version_dir):
            if os.path.exists(os.path.join(tech_version_dir, each_version, 'configs')):
                temp = []
                if each_version == 'latest':
                    real_path = os.path.realpath(os.path.join(tech_version_dir, each_version))
                    real_version = re.match(r'.*/([a-zA-Z_0-9]+)$', real_path)
                    if real_version.group(1) in already_write:
                        tech_version_list.remove([real_version.group(1), None])
                    temp.append(real_version.group(1))
                    temp.append('*')
                    tech_version_list.append(temp)
                    already_write.append(real_version.group(1))

                elif each_version not in already_write:
                    temp.append(each_version)
                    temp.append(None)
                    tech_version_list.append(temp)
                    already_write.append(each_version)
        if len(tech_version_list) > 0:
            tech_version_dict[each_tech] = tech_version_list

    flow_args_utils.print_args(tech_version_dict, logger, option_header)


def list_available_design():
    '''
    print available designs in pdflow
    '''
    import re
    import flow_log_utils
    import flow_args_utils

    logger = flow_log_utils.start_logging()

    design_dir = os.environ['DESIGN_DIR']
    option_header = ['DESIGN', 'PATH']
    designlist = []
    designs = os.listdir(design_dir)
    erase = re.compile('^\\.')
    for design in designs:
        if os.path.isfile(os.path.join(design_dir, design)) or re.match(erase, design) is not None:
            continue
        else:
            designlist.append(design)
    design_dict = {}
    for avail_design in designlist:
        design_available_dir = os.path.join(design_dir, avail_design)
        design_available_list = []
        if os.path.exists(os.path.join(design_available_dir, 'configs')):
            design_available_list.append(os.path.join(design_available_dir, 'configs'))
        if len(design_available_list) > 0:
            design_dict[avail_design] = design_available_list

    flow_args_utils.print_args(design_dict, logger, option_header)


def is_block_dir(path: str) -> bool:
    '''
    check whether the given path is a block directory (\'impl\' directory of a project environment)

    :param path: the given path
    :return: True if the given path is a block directory, False if not
    '''
    block_cfg_file = os.path.join(path, 'configs', 'block.config')
    if not os.path.exists(block_cfg_file):
        import flow_log_utils

        logger = flow_log_utils.start_logging()
        logger.error('this command should be performed under a block (impl) directory: %s does not exist' % (block_cfg_file))
        return False
    else:
        flow_config_utils.read_config(block_cfg_file)
        if not (FLOW_CFGS['BLOCK_CFG']['PROJECT'] == FLOW_CFGS['PROJECT'] and FLOW_CFGS['BLOCK_CFG']['BRANCH'] == FLOW_CFGS['BRANCH']):
            import flow_log_utils

            logger = flow_log_utils.start_logging()
            logger.error('this implementation directory is for project %s, branch %s' % (FLOW_CFGS['BLOCK_CFG']['PROJECT'], FLOW_CFGS['BLOCK_CFG']['BRANCH']))
            return False
        else:
            return True


def is_WA_dir(path: str) -> bool:
    '''
    check whether the given path is a warkarea

    :param path: the given path
    :return: True if the given path is a workarea, False if not
    '''
    wa_cfg_file = os.path.join(path, 'configs', 'wa.config')
    if not os.path.exists(wa_cfg_file):
        import flow_log_utils

        logger = flow_log_utils.start_logging()
        logger.error('this command should be performed under a workarea: %s does not exist' % (wa_cfg_file))
        return False
    else:
        flow_config_utils.read_config(wa_cfg_file)
        if not (FLOW_CFGS['WA_CFG']['PROJECT'] == FLOW_CFGS['PROJECT'] and FLOW_CFGS['WA_CFG']['BRANCH'] == FLOW_CFGS['BRANCH']):
            import flow_log_utils
            logger = flow_log_utils.start_logging()
            logger.error('this work area is for project %s, branch %s' % (FLOW_CFGS['WA_CFG']['PROJECT'], FLOW_CFGS['WA_CFG']['BRANCH']))
            return False
        else:
            return True


def is_3D_design() -> bool:
    '''
    check whether the current workarea is for 3d design (f2b or f2f) or not

    :return: True if it is for 3d designs. Otherwise, False
    '''
    import flow_utils
    from flow_config_utils import flow_cfgs as FLOW_CFGS

    if flow_utils.get_dict(FLOW_CFGS, 'WA_CFG', 'IMPL_TYPE') == 'f2b' or flow_utils.get_dict(FLOW_CFGS, 'WA_CFG', 'IMPL_TYPE') == 'f2f':
        return True
    elif flow_utils.get_dict(FLOW_CFGS, 'WA_CFG', 'IMPL_TYPE') == '2d':
        return False


def is_compact2D_flow() -> bool:
    '''
    check whether the design can be implemented with compact2D flow.
    note that compact2D flow requires 3D qrcTechFile for implementation and 3D nxtgrd for extraction
    if the files are available, it can be implemented with compact2D flow, otherwise, it needs to use the method in shrunk2D

    :return: True if it can be implemented with compact2D flow. Otherwise, False
    '''
    from flow_utils import get_dict
    from flow_config_utils import flow_cfgs as FLOW_CFGS
    from flow_env_utils import flow_envs as FLOW_ENVS

    if is_3D_design() \
        and get_dict(FLOW_CFGS, 'TECH_CFG', 'PDK', '3D', FLOW_ENVS['IMPL_TYPE'].upper(), 'QRC_ROOT_DIR') is not None \
        and get_dict(FLOW_CFGS, 'TECH_CFG', 'PDK', '3D', FLOW_ENVS['IMPL_TYPE'].upper(), 'QRC') is not None \
        and get_dict(FLOW_CFGS, 'TECH_CFG', 'PDK', '3D', FLOW_ENVS['IMPL_TYPE'].upper(), 'GRD_ROOT_DIR') is not None \
        and get_dict(FLOW_CFGS, 'TECH_CFG', 'PDK', '3D', FLOW_ENVS['IMPL_TYPE'].upper(), 'GRD') is not None:
        return True
    else:
        return False


def setup_command_log(command: str, stage: str = None, corner: str = None, extra_file_ext: str = None) -> Tuple[logging.Logger, str]:
    '''
    setup log directory and filename for pdflow commands

    :param command: command to run with pdflow
    :param stage: stage to run with pdflow
    :param extra_file_ext: you can add more extension for log filename (e.g., command.current_time.extra_file_ext.log
    :return: logger and log filename
    '''
    import flow_utils
    import flow_file_utils
    from flow_env_utils import flow_envs as FLOW_ENVS

    if stage is None:
        log_dir = os.path.join(FLOW_ENVS['WORK_AREA'], command, 'logs')
    else:
        if corner is None:
            log_dir = os.path.join(FLOW_ENVS['WORK_AREA'], command, stage, 'logs')
        else:
            log_dir = os.path.join(FLOW_ENVS['WORK_AREA'], command, stage, corner, 'logs')
    cur_time = flow_utils.get_cur_time()
    if extra_file_ext is not None:
        log_file = os.path.join(log_dir, flow_file_utils.join_filename(command, cur_time, extra_file_ext, 'log'))
    else:
        log_file = os.path.join(log_dir, flow_file_utils.join_filename(command, cur_time, 'log'))
    import flow_log_utils
    logger = flow_log_utils.start_logging(logfile=log_file)
    latest_log_file = os.path.join(log_dir, flow_file_utils.join_filename(command, 'latest', 'log'))
    flow_file_utils.make_symlink(log_file, latest_log_file)
    return logger, log_file


def setup_command_flow_env(command: str, tool: str, tool_version: str, target_flow: Union[str, None] = None, stage: Union[str, None] = None, corner: Union[str, None] = None, mode: Union[str, None] = None, logger: logging.Logger = None):
    '''
    setup basic flow environment variables for the pdflow command

    :param command: command to run with pdflow
    :param tool: tool used in the run
    :param tool_version: tool version used in the run
    :param target_flow: target flow to run with pdflow (c.f., flow: the flow you are currently running. target_flow: the flow of the design (e.g., fe, syn, pnr) which the current flow uses)
    :param stage: stage to run with pdflow
    :param corner: corner to run with pdlfow
    :param mode: mode to run with pdflow
    :param logger: logger used to log
    :return: None
    '''
    from flow_env_utils import flow_envs as FLOW_ENVS

    if logger is not None:
        import flow_log_utils

        flow_log_utils.write_subsection_comment(logger, 'setup flow env')
    FLOW_ENVS['FLOW'] = command
    if target_flow is not None:
        FLOW_ENVS['TARGET_FLOW'] = target_flow
    if stage is not None:
        FLOW_ENVS['STAGE'] = stage
    if corner is not None:
        FLOW_ENVS['CORNER'] = corner
    if mode is not None:
        FLOW_ENVS['MODE'] = mode
    FLOW_ENVS['TOOL'] = tool
    FLOW_ENVS['TOOL_VERSION'] = tool_version
    dir = os.path.join(FLOW_ENVS['WORK_AREA'], FLOW_ENVS['FLOW'])
    if target_flow is not None:
        dir = os.path.join(dir, FLOW_ENVS['TARGET_FLOW'])
    if stage is not None:
        dir = os.path.join(dir, FLOW_ENVS['STAGE'])
    if corner is not None:
        dir = os.path.join(dir, FLOW_ENVS['CORNER'])
    if mode is not None:
        dir = os.path.join(dir, FLOW_ENVS['MODE'])
    FLOW_ENVS['RUN_DIR'] = os.path.join(dir, 'work')
    FLOW_ENVS['SCRIPT_DIR'] = os.path.join(dir, 'scripts')
    FLOW_ENVS['RESULT_DIR'] = os.path.join(dir, 'results')
    FLOW_ENVS['REPORT_DIR'] = os.path.join(dir, 'reports')
    FLOW_ENVS['SESSION_DIR'] = os.path.join(dir, 'sessions')


def setup_command_dir(clean_prevrun: bool, extra_dir_flow_envs = None, logger: logging.Logger = None):
    '''
    setup directory structure for pdflow run

    :param clean_prevrun: if True, delete everything from previous run
    :param extra_dir_flow_envs: if there is any other directories to setup, make flow_envs having full path, and pass list of flow_envs keys to this variable
    :param logger: logger used to log
    :return: None
    '''
    import flow_file_utils
    from flow_env_utils import flow_envs as FLOW_ENVS

    if extra_dir_flow_envs is None:
        extra_dir_flow_envs = []
    if logger is not None:
        import flow_log_utils

        flow_log_utils.write_subsection_comment(logger, 'setup directories')
    if clean_prevrun:
        logger.info('cleanup previous run')
        flow_file_utils.delete_path(FLOW_ENVS['RUN_DIR'])
        flow_file_utils.delete_path(FLOW_ENVS['SCRIPT_DIR'])
        flow_file_utils.delete_path(FLOW_ENVS['RESULT_DIR'])
        flow_file_utils.delete_path(FLOW_ENVS['REPORT_DIR'])
        flow_file_utils.delete_path(FLOW_ENVS['SESSION_DIR'])
        for extra_dir in extra_dir_flow_envs:
            flow_file_utils.delete_path(FLOW_ENVS[extra_dir])
    flow_file_utils.make_dir(FLOW_ENVS['RUN_DIR'])
    flow_file_utils.make_dir(FLOW_ENVS['SCRIPT_DIR'])
    flow_file_utils.make_dir(FLOW_ENVS['RESULT_DIR'])
    flow_file_utils.make_dir(FLOW_ENVS['REPORT_DIR'])
    flow_file_utils.make_dir(FLOW_ENVS['SESSION_DIR'])
    for extra_dir in extra_dir_flow_envs:
        flow_file_utils.make_dir(FLOW_ENVS[extra_dir])


def has_errors(log_tracer: 'flow_log_utils.CustomStreamHandler', status: int) -> bool:
    '''
    check errors so far

    :param log_tracer: log tracer used to count errors and warnings
    :param status: status of current run so far (0 for no problem. otherwise, 1)
    :return: True if there is any error so far. Otherwise False
    '''
    if len(log_tracer.criticals) > 0 or len(log_tracer.errors) > 0 or status != 0:
        return True
    else:
        return False


def has_memory() -> bool:
    '''
    check whether design has memory blocks

    :return: True if design has memory block. Otherwise, False
    '''
    from flow_var_utils import flow_vars as FLOW_VARS

    if FLOW_VARS['MEMORY_CELLS'] is not None and len(FLOW_VARS['MEMORY_CELLS']) > 0:
        return True
    else:
        return False


def setup_command_interactive_dir() -> str:
    '''
    setup interactive directory

    :return: basename of the interactive directory
    '''
    import flow_utils
    import flow_file_utils
    from flow_env_utils import flow_envs as FLOW_ENVS

    cur_time = flow_utils.get_cur_time()
    interactive_name = FLOW_ENVS['USER'] + '-' + cur_time
    FLOW_ENVS['INTERACTIVE_DIR'] = os.path.join(FLOW_ENVS['RUN_DIR'], 'interactive_sessions', interactive_name)
    flow_file_utils.make_dir(FLOW_ENVS['INTERACTIVE_DIR'])
    return interactive_name


def write_file_list(file_list_file: str, file_list: List[str]):
    '''
    store list of filenames to a file

    :param file_list_file: filename to store list of filenames
    :param file_list: list of filenames
    :return: None
    '''
    import flow_file_utils

    ofp = flow_file_utils.open_wfile(file_list_file, force=True)
    realpath_file_list = [os.path.realpath(os.path.expanduser(file)) for file in file_list]
    realpath_file_list = list(set(realpath_file_list))
    realpath_file_list.sort()
    for input_collateral in realpath_file_list:
        ofp.write('%s\n' % (input_collateral))
    ofp.close()


def read_file_list(file_list_file: str) -> List[str]:
    '''
    read list of filename from a file

    :param file_list_file: filename to read list of filenames
    :return: list of filenames
    '''
    import flow_file_utils
    file_list = []
    ifp = flow_file_utils.open_rfile(file_list_file)
    for line in ifp:
        file_list.append(line.strip())
    ifp.close()
    return file_list


def check_file_list(file_list: List[str], logger: logging.Logger) -> int:
    '''
    check whether all the files in the list of filenames exist or not

    :param file_list: list of filenames to check
    :param logger: logger used to log
    :return: 0 if all the files exist. Otherwise 1.
    '''
    ret = 0
    realpath_file_list = [os.path.realpath(os.path.expanduser(file)) for file in file_list]
    realpath_file_list = list(set(realpath_file_list))
    realpath_file_list.sort()
    for file in realpath_file_list:
        if not os.path.exists(file):
            logger.error('file missing: %s' % (file))
            ret = 1
        else:
            logger.info('file exists : %s' % (file))
    return ret


def dump_flow_envs_cfgs_vars(dir: str):
    '''
    dump flow_envs and flow_cfgs as json files, and flow_vars as python file

    :param dir: directory to store those files
    :return: None
    '''
    import json

    import flow_file_utils
    import flow_var_utils
    from flow_env_utils import flow_envs as FLOW_ENVS
    from flow_config_utils import flow_cfgs as FLOW_CFGS
    from flow_var_utils import flow_vars as FLOW_VARS

    ofp = flow_file_utils.open_wfile(os.path.join(dir, flow_file_utils.join_filename('flow_envs', 'json')), 'w')
    json.dump(FLOW_ENVS, ofp, indent=2)
    ofp.close()
    ofp = flow_file_utils.open_wfile(os.path.join(dir, flow_file_utils.join_filename('flow_cfgs', 'json')), 'w')
    json.dump(FLOW_CFGS, ofp, indent=2)
    ofp.close()
    flow_var_utils.write_vars(os.path.join(dir, flow_file_utils.join_filename('flow_vars', 'py')))
    ofp = flow_file_utils.open_wfile(os.path.join(dir, flow_file_utils.join_filename('flow_vars', 'json')), 'w')
    json.dump(FLOW_VARS, ofp, indent=2)
    ofp.close()


############################################################
# PDFLOW COMMAND FUNCTIONS
############################################################
def add_block(tech_name: str, design: str, block: str, flat: bool) -> int:
    '''
    add a block of a design in the project environment to be implemented. this command should be performed in a project environment (pe)

    :param tech_name: process node used for implementation. check "pdflow.py list_tech" for available processes. format: <process_dir> for the latest version, <process_dir>/<ver_dir> for specific version. e.g., to use tech/NANGATE45/2020_10, -tech NANGATE45/2020_10
    :param design: design to implement. check "pdflow.py list_design" for available designs. format: <design_dir>. e.g., to use designs/aes_128, -design aes_128
    :param block: implement only block in a design. to check the hierarchy, see design.config
    :param flat: boolean to flatten all sub-hierarchy of the specified block
    :return: 0 if this function ends successfully
    '''
    import flow_config_utils
    from flow_config_utils import flow_cfgs as FLOW_CFGS
    import flow_log_utils
    import flow_file_utils

    # check whether the command is submitted in the right directory
    cur_dir = os.getcwd()
    if not project.is_pe_dir(cur_dir):
        sys.exit()

    # start logging once the command is valid
    logger = flow_log_utils.start_logging()
    flow_log_utils.write_section_comment(logger, 'add_block command')

    # read design config
    design_cfg_file = os.path.join(os.getenv('DESIGN_DIR'), design, 'configs', 'design.config')
    if not os.path.exists(design_cfg_file):
        logger.error('design config %s does not exist' % (design_cfg_file))
        sys.exit()
    else:
        flow_config_utils.read_config(design_cfg_file)
        check_design(design, block)

    # get tech name and tech version
    tech, tech_version = get_tech_version(tech_name)
    if not os.path.exists(os.path.join(os.getenv('TECH_DIR'), tech, tech_version)):
        logger.error('specified tech %s does not exist in %s' % (tech_name, os.path.exists(os.path.join(os.getenv('TECH_DIR'), tech, tech_version))))
        sys.exit()
    else:
        # resolve link
        tech_version = os.path.basename(os.path.realpath(os.path.join(os.getenv('TECH_DIR'), tech, tech_version)))
        tech_name = tech + '/' + tech_version

    # read tech config
    tech_cfg_file = os.path.join(os.getenv('TECH_DIR'), tech, tech_version, 'configs', 'tech.config')
    if not os.path.exists(tech_cfg_file):
        logger.error('tech config %s does not exist' % (tech_cfg_file))
        sys.exit()
    else:
        flow_config_utils.read_config(tech_cfg_file)

    # read pe config
    pe_cfg_file = os.path.join(cur_dir, 'configs', 'pe.config')
    flow_config_utils.read_config(pe_cfg_file)

    # block(impl) directory
    if block is None:
        block = design
    impl_dir = os.path.join(os.getcwd(), FLOW_CFGS['PE_CFG']['PROJECT'], design, block, tech, tech_version, 'impl')
    if os.path.exists(impl_dir):
        logger.error('implementation directory %s already exists' % (impl_dir))
        sys.exit()

    # create block(impl) directory
    flow_file_utils.make_dir(impl_dir)
    flow_file_utils.make_dir(os.path.join(impl_dir, 'configs'))

    # create block config file
    block_cfg = {}
    block_cfg['BLOCK_CFG'] = {}
    block_cfg['BLOCK_CFG']['PROJECT'] = FLOW_CFGS['PROJECT']
    block_cfg['BLOCK_CFG']['BRANCH'] = FLOW_CFGS['BRANCH']
    block_cfg['BLOCK_CFG']['TECH'] = tech_name
    block_cfg['BLOCK_CFG']['DESIGN'] = design
    block_cfg['BLOCK_CFG']['BLOCK'] = block
    block_cfg['BLOCK_CFG']['FLAT'] = flat
    flow_config_utils.write_config(block_cfg, os.path.join(impl_dir, 'configs', 'block.config'))

    return 0


def create_wa(wa_name: str, handoff_id: str, impl_type: str, impl_method: str) -> int:
    '''
    create a workarea to perform physical design. this command should be performed in block directory (\'impl\' directory of a project environment)

    :param wa_name: name of workarea. this will become directory name.
    :param handoff_id: handoff id under the handoff directory of the project, from which the sub-hierarchy designs are being used
    :param impl_type: implementation type of the design (2d, f2b(3d), f2f(3d))
    :param impl_method: implementation method of 3d design. required only when -impl_type is f2b or f2f
    :return: 0 if this function ends successfully
    '''
    import flow_config_utils
    from flow_config_utils import flow_cfgs as FLOW_CFGS
    import flow_log_utils
    import flow_file_utils
    import flow_git_utils

    # check whether the command is submitted in the right directory
    cur_dir = os.getcwd()
    if not is_block_dir(cur_dir):
        sys.exit()

    # start logging once the command is valid
    logger = flow_log_utils.start_logging()
    flow_log_utils.write_section_comment(logger, 'create_wa command')

    # validate options
    wa_dir = os.path.join(cur_dir, wa_name)
    if os.path.exists(wa_dir):
        logger.error('workarea %s already exist' % (wa_dir))
        sys.exit()
    if handoff_id is not None:
        if not os.path.exists(os.path.join(FLOW_CFGS['HANDOFF_DIR'], handoff_id)):
            logger.error('-handoff_id %s does not exist in project handoff directory %s' % (handoff_id, FLOW_CFGS['HANDOFF_DIR']))
            sys.exit()

    # read block config
    block_cfg_file = os.path.join(cur_dir, 'configs', 'block.config')
    flow_config_utils.read_config(block_cfg_file)

    # create workarea directories
    wa_default_dirs = ['library', 'scripts', 'logs', 'history', 'fe', 'interface', 'configs']
    wa_sub_dirs = wa_default_dirs + supported_flows
    for wa_sub_dir in wa_sub_dirs:
        flow_file_utils.make_dir(os.path.join(wa_dir, wa_sub_dir))
    tech_dir = os.path.join(os.getenv('TECH_DIR'), FLOW_CFGS['BLOCK_CFG']['TECH'])
    wa_library_dir = os.path.join(wa_dir, 'library')
    for wa_sub_dir in os.listdir(tech_dir):
        flow_file_utils.make_symlink(os.path.join(tech_dir, wa_sub_dir), os.path.join(wa_library_dir, wa_sub_dir))
    wa_scripts_dir = os.path.join(wa_dir, 'scripts')
    logger.info('cloning script directory from remote repo')
    repo = flow_git_utils.clone_from_remote('projects', wa_scripts_dir, path_in_remote=FLOW_CFGS['BLOCK_CFG']['PROJECT'])
    design_dir = os.path.join(os.getenv('DESIGN_DIR'), FLOW_CFGS['BLOCK_CFG']['DESIGN'])
    wa_fe_dir = os.path.join(wa_dir, 'fe')
    for path in os.listdir(design_dir):
        flow_file_utils.make_symlink(os.path.join(design_dir, path), os.path.join(wa_fe_dir, path))
    if handoff_id is not None:
        handoff_dir = os.path.join(FLOW_CFGS['HANDOFF_DIR'], handoff_id)
        wa_interface_dir = os.path.join(wa_dir, 'interface')
        for path in os.listdir(handoff_dir):
            flow_file_utils.make_symlink(os.path.join(handoff_dir, path), os.path.join(wa_interface_dir, path))

    # create workarea config file
    wa_cfg = {}
    wa_cfg['WA_CFG'] = {}
    wa_cfg['WA_CFG']['PROJECT'] = FLOW_CFGS['PROJECT']
    wa_cfg['WA_CFG']['BRANCH'] = FLOW_CFGS['BRANCH']
    wa_cfg['WA_CFG']['TECH'] = FLOW_CFGS['BLOCK_CFG']['TECH']
    wa_cfg['WA_CFG']['DESIGN'] = FLOW_CFGS['BLOCK_CFG']['DESIGN']
    wa_cfg['WA_CFG']['BLOCK'] = FLOW_CFGS['BLOCK_CFG']['BLOCK']
    wa_cfg['WA_CFG']['FLAT'] = FLOW_CFGS['BLOCK_CFG']['FLAT']
    wa_cfg['WA_CFG']['DIR'] = os.path.join(cur_dir, wa_name)
    wa_cfg['WA_CFG']['IMPL_TYPE'] = impl_type
    if impl_type == 'f2b' or impl_type == 'f2f':
        wa_cfg['WA_CFG']['IMPL_METHOD'] = impl_method
    flow_config_utils.write_config(wa_cfg, os.path.join(cur_dir, wa_name, 'configs', 'wa.config'))

    return 0


def clone_wa(src: str, dest: str, stages: str, flows: List[str], aslink: bool) -> int:
    '''
    clone a workarea with the same project environment. this command should be performed in block directory (\'impl\' directory of a project environment)

    :param src: directory path to the source workarea
    :param dest: name of the cloned workarea
    :param stages: specify the stages to be cloned. you can specify multiple stages. if not specified, it will clone every stages
    :param flows: specify the flows to be cloned. you can specify multiple flows. if not specified, it will clone every flows
    :param aslink: all the cloned files are created as symbolic links
    :return: 0 if this function ends successfully
    '''
    import flow_config_utils
    from flow_config_utils import flow_cfgs as FLOW_CFGS
    import flow_log_utils
    import flow_file_utils

    # check whether the command is submitted in the right directory
    cur_dir = os.getcwd()
    if not is_block_dir(cur_dir):
        sys.exit()

    # start logging once the command is valid
    logger = flow_log_utils.start_logging()
    flow_log_utils.write_section_comment(logger, 'clone_wa command')

    # validate options
    src = os.path.abspath(src)
    dest = os.path.abspath(dest)
    if not os.path.exists(src):
        logger.error('source workarea %s does not exist' % (src))
        sys.exit()
    wa_dir = os.path.join(cur_dir, dest)
    if os.path.exists(wa_dir):
        logger.error('workarea %s already exist' % (wa_dir))
        sys.exit()

    block_cfg_file = os.path.join(cur_dir, 'configs', 'block.config')
    flow_config_utils.read_config(block_cfg_file)
    src_wa_cfg_file = os.path.join(src, 'configs', 'wa.config')
    flow_config_utils.read_config(src_wa_cfg_file)
    if FLOW_CFGS['BLOCK_CFG']['PROJECT'] != FLOW_CFGS['WA_CFG']['PROJECT'] \
            or FLOW_CFGS['BLOCK_CFG']['BRANCH'] != FLOW_CFGS['WA_CFG']['BRANCH'] \
            or FLOW_CFGS['BLOCK_CFG']['TECH'] != FLOW_CFGS['WA_CFG']['TECH'] \
            or FLOW_CFGS['BLOCK_CFG']['DESIGN'] != FLOW_CFGS['WA_CFG']['DESIGN'] \
            or FLOW_CFGS['BLOCK_CFG']['BLOCK'] != FLOW_CFGS['WA_CFG']['BLOCK'] \
            or FLOW_CFGS['BLOCK_CFG']['FLAT'] != FLOW_CFGS['WA_CFG']['FLAT']:
        logger.error('project/design setup of the source workarea is different from the destination workarea')
        sys.exit()

    if stages is None:
        if FLOW_CFGS['WA_CFG']['IMPL_TYPE'] == 'f2b' or FLOW_CFGS['WA_CFG']['IMPL_TYPE'] == 'f2f':
            stages = supported_pnr_3d_stages
        else:
            stages = supported_pnr_2d_stages

    if flows is None:
        temp_flows = supported_flows[:]
    else:
        temp_flows = flows[:]
    flows = []
    for targ_flow in temp_flows:
        if targ_flow not in supported_flows:
            logger.error('invalid flow %s in -flow' % (targ_flow))
            sys.exit()
        stage_exists = False
        for targ_stage in stages:
            if os.path.exists(os.path.join(src, targ_flow, targ_stage)):
                stage_exists = True
        if not stage_exists:
            logger.warning('stage %s does not exist in flow %s' % (stages, targ_flow))
        else:
            flows.append(targ_flow)

    wa_copy_default_dirs = ['library', 'scripts', 'fe', 'interface']
    wa_link_default_dirs = ['logs', 'history']
    wa_link_flow_dirs = flows
    for wa_sub_dir in wa_copy_default_dirs:
        flow_file_utils.copy_path(os.path.join(src, wa_sub_dir), os.path.join(wa_dir, wa_sub_dir))
    for wa_sub_dir in wa_link_default_dirs:
        if aslink:
            flow_file_utils.make_symlink(os.path.join(src, wa_sub_dir), os.path.join(wa_dir, wa_sub_dir), preserve_dirs=True)
        else:
            flow_file_utils.copy_path(os.path.join(src, wa_sub_dir), os.path.join(wa_dir, wa_sub_dir))
    for wa_sub_dir in supported_flows:
        flow_file_utils.make_dir(os.path.join(wa_dir, wa_sub_dir))
        if wa_sub_dir in wa_link_flow_dirs:
            for stage in stages:
                if aslink:
                    flow_file_utils.make_symlink(os.path.join(src, wa_sub_dir, stage), os.path.join(wa_dir, wa_sub_dir, stage), preserve_dirs=True)
                else:
                    flow_file_utils.copy_path(os.path.join(src, wa_sub_dir, stage), os.path.join(wa_dir, wa_sub_dir, stage))
    wa_config_dir = os.path.join(wa_dir, 'configs')
    flow_file_utils.make_dir(wa_config_dir)

    # create workarea config file
    wa_cfg = {}
    wa_cfg['WA_CFG'] = {}
    wa_cfg['WA_CFG']['PROJECT'] = FLOW_CFGS['PROJECT']
    wa_cfg['WA_CFG']['BRANCH'] = FLOW_CFGS['BRANCH']
    wa_cfg['WA_CFG']['TECH'] = FLOW_CFGS['BLOCK_CFG']['TECH']
    wa_cfg['WA_CFG']['DESIGN'] = FLOW_CFGS['BLOCK_CFG']['DESIGN']
    wa_cfg['WA_CFG']['BLOCK'] = FLOW_CFGS['BLOCK_CFG']['BLOCK']
    wa_cfg['WA_CFG']['FLAT'] = FLOW_CFGS['BLOCK_CFG']['FLAT']
    wa_cfg['WA_CFG']['DIR'] = os.path.join(cur_dir, dest)
    wa_cfg['WA_CFG']['IMPL_TYPE'] = FLOW_CFGS['WA_CFG']['IMPL_TYPE']
    if FLOW_CFGS['WA_CFG']['IMPL_TYPE'] == 'f2b' or FLOW_CFGS['WA_CFG']['IMPL_TYPE'] == 'f2f':
        wa_cfg['WA_CFG']['IMPL_METHOD'] = FLOW_CFGS['WA_CFG']['IMPL_METHOD']
    flow_config_utils.write_config(wa_cfg, os.path.join(cur_dir, dest, 'configs', 'wa.config'))

    flow_file_utils.make_symlink(src, os.path.join(wa_dir, 'clone_src'))

    return 0


def handoff(handoff_id: str) -> int:
    '''
    TODO: NEED TO IMPLEMENT
    handoff the current workarea. this command should be performed in a workarea (wa)

    :param handoff_id: handoff the design of the current workarea in the handoff directory of the project with the specified handoff id
    :return: 0 if this function ends successfully
    '''
    import flow_config_utils
    from flow_config_utils import flow_cfgs as FLOW_CFGS
    import flow_log_utils

    # check whether the command is submitted in the right directory
    cur_dir = os.getcwd()
    if not is_WA_dir(cur_dir):
        sys.exit()

    # start logging once the command is valid
    logger = flow_log_utils.start_logging()
    flow_log_utils.write_section_comment(logger, 'handoff command')

    # validate options
    wa_cfg_file = os.path.join(cur_dir, 'configs', 'wa.config')
    flow_config_utils.read_config(wa_cfg_file)
    design = FLOW_CFGS['WA_CFG']['DESIGN']
    block = FLOW_CFGS['WA_CFG']['BLOCK']
    if os.path.exists(os.path.join(FLOW_CFGS['HANDOFF_DIR'], handoff_id, design, block)):
        pass
    # TODO: read handoff.config and copy selected file to handoff directory

    # read block config

    return 0


def update_interface(handoff_id: str, block: str) -> int:
    '''
    TODO: NEED TO IMPLEMENT
    update interface of the current workarea. this command should be performed in a workarea (wa)

    :param handoff_id: update the handoff id of the sub-hierarchy designs
    :param block: limit the update to the block
    :return: 0 if this function ends successfully
    '''
    import flow_log_utils

    # check whether the command is submitted in the right directory
    cur_dir = os.getcwd()
    if not is_WA_dir(cur_dir):
        sys.exit()

    # start logging once the command is valid
    logger = flow_log_utils.start_logging()
    flow_log_utils.write_section_comment(logger, 'update_interface command')

    # validate options
    # TODO

    # read config
    return 0


def history(all: bool, num: int) -> int:
    '''
    show command history of the current workarea. by default, show only the last 10 history. this command should be performed in a workarea (wa)

    :param all: boolean to control to show all history
    :param num: show only the last <num> history
    :return: 0 if this function ends successfully
    '''
    # check whether the command is submitted in the right directory
    cur_dir = os.getcwd()
    if not is_WA_dir(cur_dir):
        sys.exit()

    # don't do logging
    all_cmd_files = sorted(os.listdir(os.path.join(cur_dir, 'history')))
    num_history = len(all_cmd_files)
    if all:
        selected_cmd_files = all_cmd_files
        start_num = 1
    elif num is not None:
        selected_cmd_files = all_cmd_files[-num:]
        start_num = num_history - num
    else:
        selected_cmd_files = all_cmd_files[-10:]
        start_num = max(num_history - 10, 1)

    for i, cmd_file in enumerate(selected_cmd_files):
        cmd_file_path = os.path.join(cur_dir, 'history', cmd_file)
        with open(cmd_file_path, 'r') as ifp:
            for line in ifp:
                match = re.search('# Created = (?P<date_time>\S+)', line)
                if match:
                    date_time = match.group('date_time')
                match = re.match(r'^[^#]', line)
                if match:
                    command = line.strip()
        print('%d %s %s' % (start_num + i, date_time, command))

    return 0


if __name__ == '__main__':
    pdflow_args = parser.parse_args()

    command = pdflow_args.command
    ovdir = pdflow_args.ovdir
    debug_mode = pdflow_args.debug

    if os.getenv('PROJECT') == 'common':
        import flow_log_utils

        logger = flow_log_utils.start_logging()
        logger.error('pdflow should be performed under project other than \'common\'')
        sys.exit()

    cur_dir = os.getcwd()

    # setup ovdir
    if ovdir is not None:
        import set_ovdir

        set_ovdir.set_ovdir_for_run('ce', ovdir)

    if debug_mode:
        os.environ['DEBUG'] = '1'

    ###################################
    # NEED TO LOAD CUSTOM PACKAGES AFTER SETTING UP OVDIR
    ###################################
    from flow_utils import *
    # top-level binary should initialize flow_cfg at the very first as it can be used in pdflow and ldflow
    import flow_config_utils

    flow_config_utils.init()
    from flow_config_utils import flow_cfgs as FLOW_CFGS
    import flow_env_utils

    flow_env_utils.init()
    from flow_env_utils import flow_envs as FLOW_ENVS
    import flow_var_utils

    flow_var_utils.init()
    from flow_var_utils import flow_vars as FLOW_VARS
    import flow_log_utils
    import flow_args_utils
    import flow_file_utils
    import flow_git_utils
    import project

    # execute commands which does not require logging
    if command == 'list_tech':
        list_available_tech()
        sys.exit()
    elif command == 'list_design':
        list_available_design()
        sys.exit()

    # setup logs
    log_dir = os.path.join(cur_dir, 'logs')
    if not os.path.exists(log_dir):
        flow_file_utils.make_dir(log_dir)
    cur_time = get_cur_time()
    log_file = os.path.join(log_dir, 'pdflow.' + command + '.' + cur_time + '.log')
    logger = flow_log_utils.start_logging(logfile=log_file)
    log_tracer = flow_log_utils.add_logging_tracker(logger)
    latest_log_file = os.path.join(log_dir, 'pdflow.latest.log')
    flow_file_utils.make_symlink(log_file, latest_log_file)

    # let's leave a note about ovdir in the log
    if ovdir is not None:
        logger.warning('ovdir %s detected' % (os.path.abspath(ovdir)))

    # print out given arguments
    flow_args_utils.print_args(pdflow_args, logger=logger)

    # for all commands running in workarea, create history for commands
    if command not in ['add_block', 'create_wa', 'clone_wa', 'history']:
        input_command = ' '.join(sys.argv)
        create_history(input_command, cur_time, log_file)

    # read project config
    proj_cfg_file = os.path.join(os.getenv('ENV_DIR'), 'configs', 'project.' + FLOW_CFGS['PROJECT_BRANCH'] + '.config')
    flow_config_utils.read_config(proj_cfg_file)

    # set flow envs
    FLOW_ENVS['USER'] = FLOW_CFGS['USER']
    FLOW_ENVS['HOST'] = FLOW_CFGS['HOST']
    FLOW_ENVS['PROJECT'] = FLOW_CFGS['PROJECT']
    FLOW_ENVS['BRANCH'] = FLOW_CFGS['BRANCH']
    FLOW_ENVS['CE_VERSION'] = FLOW_CFGS['CE_VERSION']
    FLOW_ENVS['CE_DIR'] = FLOW_CFGS['CE_DIR']
    FLOW_ENVS['HANDOFF_DIR'] = FLOW_CFGS['HANDOFF_DIR']
    FLOW_ENVS['PROJECT_BRANCH'] = FLOW_CFGS['PROJECT_BRANCH']
    if os.getenv('CE_OVDIR') is not None:
        FLOW_ENVS['CE_OVDIR'] = os.getenv('CE_OVDIR')

    # warn flow vars from command-line
    if pdflow_args.setvar is not None:
        flow_var_utils.set_vars_from_cli = pdflow_args.setvar
        for flow_var_str in flow_var_utils.set_vars_from_cli:
            logger.warning('set flow variable from command-line (highest priority): %s' % (flow_var_str))

    ret = 0

    # execute the commands
    if command == 'add_block':
        ret |= add_block(pdflow_args.tech, pdflow_args.design, pdflow_args.block, pdflow_args.flat)
    elif command == 'create_wa':
        ret |= create_wa(pdflow_args.name, pdflow_args.handoff_id, pdflow_args.impl_type, pdflow_args.impl_method)
    elif command == 'clone_wa':
        ret |= clone_wa(pdflow_args.src, pdflow_args.dest, pdflow_args.stage, pdflow_args.flow, pdflow_args.aslink)
    elif command == 'handoff':
        ret |= handoff(pdflow_args.handoff_id)
    elif command == 'update_interface':
        ret |= update_interface(pdflow_args.handoff_id, pdflow_args.block)
    elif command == 'history':
        ret |= history(pdflow_args.all, pdflow_args.num)
    else:
        FLOW_ENVS['TECH'] = FLOW_CFGS['WA_CFG']['TECH']
        FLOW_ENVS['DESIGN'] = FLOW_CFGS['WA_CFG']['DESIGN']
        FLOW_ENVS['BLOCK'] = FLOW_CFGS['WA_CFG']['BLOCK']
        FLOW_ENVS['FLAT'] = FLOW_CFGS['WA_CFG']['FLAT']
        FLOW_ENVS['WORK_AREA'] = FLOW_CFGS['WA_CFG']['DIR']
        FLOW_ENVS['IMPL_TYPE'] = FLOW_CFGS['WA_CFG']['IMPL_TYPE']
        if is_3D_design():
            FLOW_ENVS['IMPL_METHOD'] = FLOW_CFGS['WA_CFG']['IMPL_METHOD']

        if command == 'syn':
            import pdflow_syn

            ret |= pdflow_syn.run_syn(pdflow_args.tool, pdflow_args.tool_version, pdflow_args.clean_prevrun, pdflow_args.run, log_tracer)
        elif command == 'pnr':
            import pdflow_pnr

            if is_3D_design():
                supported_pnr_stages = supported_pnr_3d_stages
            else:
                supported_pnr_stages = supported_pnr_2d_stages
            if pdflow_args.stage is not None and pdflow_args.stage not in supported_pnr_stages:
                if is_3D_design():
                    impl_method_str = ' method %s' % FLOW_ENVS['IMPL_METHOD']
                else:
                    impl_method_str = ''
                logger.error('stage %s is not supported in the implementation type %s%s' % (pdflow_args.stage, FLOW_ENVS['IMPL_TYPE'], impl_method_str))
                sys.exit()
            ret |= pdflow_pnr.run_pnr(pdflow_args.stage, pdflow_args.tool, pdflow_args.tool_version, pdflow_args.clean_prevrun, pdflow_args.run, pdflow_args.design, log_tracer)
        elif command == 'ext':
            import pdflow_ext

            ret |= pdflow_ext.run_ext(pdflow_args.stage, pdflow_args.corner, pdflow_args.tool, pdflow_args.tool_version, pdflow_args.clean_prevrun, pdflow_args.run, log_tracer)
        elif command == 'sta':
            import pdflow_sta

            ret |= pdflow_sta.run_sta(pdflow_args.stage, pdflow_args.corner, pdflow_args.tool, pdflow_args.tool_version, pdflow_args.clean_prevrun, pdflow_args.run, log_tracer)
        elif command == 'emir':
            import pdflow_emir

            ret |= pdflow_emir.run_emir(pdflow_args.stage, pdflow_args.mode, pdflow_args.tool, pdflow_args.tool_version, pdflow_args.clean_prevrun, pdflow_args.run, log_tracer)
        elif command == 'sim':
            import pdflow_sim

            ret |= pdflow_sim.run_sim(pdflow_args.target_flow, pdflow_args.stage, pdflow_args.tool, pdflow_args.tool_version, pdflow_args.clean_prevrun, pdflow_args.run, log_tracer)

    # finalize pdflow
    # perform command run summary in each flow,
    # since some flows need to run several times and stop running depending on the summary result
    if has_errors(log_tracer, ret):
        logger.error('PDFLOW FAILED WITH ERRORS')
    else:
        logger.info('PDFLOW FINISHED SUCCESSFULLY')

    exit(ret)
