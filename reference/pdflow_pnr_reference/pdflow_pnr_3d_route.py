import gen_db
import pdflow
import pdflow_pnr

from flow_utils import *
import flow_tcl_utils
import flow_file_utils
import flow_log_utils

import pdflow_lefdef_utils
import pdflow_gds_utils
import pdflow_grd_utils
import liberty_nldm

from flow_var_utils import flow_vars as FLOW_VARS
from flow_config_utils import flow_cfgs as FLOW_CFGS
from flow_env_utils import flow_envs as FLOW_ENVS

logger = flow_log_utils.start_logging()


def write_tcl(filename: str, mmmc_file: Union[str, None], cpf_file: Union[str, None], upf_file: Union[str, None], options_file: str) -> int:
	'''
	write a script to route 3d designs (merged design) in order to determine the locations of 3d vias

	:param filename: path to innovus script
	:param mmmc_file: path to mmmc file
	:param cpf_file: path to cpf file
	:param upf_file: path to upf file
	:param options_file: path to options file
	:return: 0 if script is generated successfully. Otherwise, 1
	'''
	ret = 0

	pnr_3d_route_tcl = flow_tcl_utils.TclFile(filename=filename)

	pdflow_pnr.innovus_start_commands(pnr_3d_route_tcl, restore_design=False)
	netlist_file = os.path.join(FLOW_ENVS['RESULT_DIR'], flow_file_utils.join_filename(FLOW_ENVS['BLOCK'], 'input', 'v'))
	pnr_3d_route_tcl.write('set init_verilog %s' % (netlist_file))
	pdflow_pnr.pnr_input_collaterals.append(netlist_file)

	lef_files = [os.path.join(FLOW_ENVS['RESULT_DIR'], flow_file_utils.join_filename(FLOW_ENVS['BLOCK'], 'lef'))]
	pnr_3d_route_tcl.write('set init_lef_file %s' % (flow_tcl_utils.get_list(lef_files)))
	pdflow_pnr.pnr_input_collaterals += lef_files

	pwr_net = get_dict(FLOW_VARS, 'DEFAULT_PWR_NET')
	gnd_net = get_dict(FLOW_VARS, 'DEFAULT_GND_NET')
	pnr_3d_route_tcl.write('set init_pwr_net %s' % (pwr_net))
	pnr_3d_route_tcl.write('set init_gnd_net %s' % (gnd_net))
	pnr_3d_route_tcl.write('set init_top_cell %s' % (FLOW_ENVS['BLOCK']))
	if pdflow.is_compact2D_flow():
		pnr_3d_route_tcl.write('set init_mmmc_file %s' % (mmmc_file))
		pdflow_pnr.pnr_input_collaterals.append(mmmc_file)
	pnr_3d_route_tcl.write('init_design')
	pnr_3d_route_tcl.write('')
	if upf_file is not None:
		pnr_3d_route_tcl.write('read_power_intent -1801 %s' % (upf_file))
		pdflow_pnr.pnr_input_collaterals.append(upf_file)
	elif cpf_file is not None:
		pnr_3d_route_tcl.write('read_power_intent -cpf %s' % (cpf_file))
		pdflow_pnr.pnr_input_collaterals.append(cpf_file)
	else:
		logger.warning('power intent file does not exist.')
	pnr_3d_route_tcl.write('commit_power_intent')
	pnr_3d_route_tcl.write('')
	pnr_3d_route_tcl.write('source %s' % (options_file))
	pdflow_pnr.pnr_input_collaterals.append(options_file)

	input_floorplan_def_file = os.path.join(FLOW_ENVS['RESULT_DIR'], flow_file_utils.join_filename(FLOW_ENVS['BLOCK'], 'input', 'floorplan', 'def'))
	pnr_3d_route_tcl.write('defIn %s' % (input_floorplan_def_file))
	pdflow_pnr.pnr_input_collaterals.append(input_floorplan_def_file)
	rail_spec = get_dict(FLOW_VARS, 'PNR_FPLAN_RAIL_SPEC')
	bump_size = get_dict(FLOW_VARS, 'PNR_FPLAN_BUMP_SIZE')
	bump_pitch = get_dict(FLOW_VARS, 'PNR_FPLAN_BUMP_PITCH')
	if rail_spec is not None and bump_size is not None and bump_pitch is not None:
		pnr_3d_route_tcl.write_section_comment('power plan')
		pnr_3d_route_tcl.write('package require pdflowEDI_design_utils')
		pnr_3d_route_tcl.write('')
		bottom_routing_layer = get_dict(FLOW_CFGS, 'TECH_CFG', 'PNR', 'ROUTE', 'BOTTOM_ROUTING_LAYER')
		if bottom_routing_layer is None:
			logger.warning('FLOW_CFGS[TECH_CFG:PNR:ROUTE:BOTTOM_ROUTING_LAYER] not defined. assuming 1')
			bottom_routing_layer = 1
		build_pdn_opt = {
			'-imp_type': '3d_'+get_dict(FLOW_ENVS, 'IMPL_TYPE'),
			'-imp_method': FLOW_ENVS['IMPL_METHOD'],
			'-pwr_net': get_dict(FLOW_VARS, 'DEFAULT_PWR_NET'),
			'-gnd_net': get_dict(FLOW_VARS, 'DEFAULT_GND_NET'),
			'-pwr_pins': '[lsort -unique [dbGet [dbGet -p head.libCells.pgTerms.pgType primaryPower].name]]',
			'-gnd_pins': '[lsort -unique [dbGet [dbGet -p head.libCells.pgTerms.pgType primaryGround].name]]',
			'-bump_size': bump_size,
			'-bump_pitch': bump_pitch,
			'-rail_spec': flow_tcl_utils.get_array(get_dict(FLOW_VARS, 'PNR_FPLAN_RAIL_SPEC')),
			'-bottom_routing_layer': bottom_routing_layer,
			'-output_dir': FLOW_ENVS['RESULT_DIR'],
			'-output_prefix': FLOW_ENVS['BLOCK'],
		}
		core_ring_spec = get_dict(FLOW_VARS, 'PNR_FPLAN_CORE_RING_SPEC')
		if core_ring_spec is not None:
			build_pdn_opt['-core_ring_spec'] = flow_tcl_utils.get_array(core_ring_spec)
		block_ring_spec = get_dict(FLOW_VARS, 'PNR_FPLAN_BLOCK_RING_SPEC')
		if block_ring_spec is not None:
			logger.error(block_ring_spec)
			build_pdn_opt['-block_ring_spec'] = flow_tcl_utils.get_array(block_ring_spec)
		if FLOW_ENVS['IMPL_TYPE'] == 'f2f':
			build_pdn_opt['-pwr_tsv_size'] = FLOW_VARS['PNR_FPLAN_PWR_TSV_SIZE']
			build_pdn_opt['-pwr_tsv_pitch'] = FLOW_VARS['PNR_FPLAN_PWR_TSV_PITCH']
		pnr_3d_route_tcl.write_cmd_w_opts('pdflowEDI_design_utils::build_pdn', build_pdn_opt)

	input_def_file = os.path.join(FLOW_ENVS['RESULT_DIR'], flow_file_utils.join_filename(FLOW_ENVS['BLOCK'], 'input', 'def'))
	pnr_3d_route_tcl.write('defIn %s' % (input_def_file))
	pdflow_pnr.pnr_input_collaterals.append(input_def_file)

	nanoroute_mode_opts = {}
	nanoroute_mode_opts['-drouteEndIteration'] = 10
	if not pdflow.is_compact2D_flow():
		# **ERROR: (IMPDC-634): Failed to build the timing graph since timing library files have not yet been loaded. To resolve this, check that timing library files have been correctly specified in the loaded design database.
		nanoroute_mode_opts['-routeWithTimingDriven'] = 'false'
		nanoroute_mode_opts['-routeWithSiDriven'] = 'false'
	pnr_3d_route_tcl.write_cmd_w_opts('setNanoRouteMode', nanoroute_mode_opts)

	session_dir = pdflow_pnr.get_session_file(FLOW_ENVS['STAGE'], 'pre_' + FLOW_ENVS['BLOCK'])
	save_design_opts = {
		session_dir: None,
		'-compress': None,
		'-verilog': None,
	}
	pnr_3d_route_tcl.write_cmd_w_opts('saveDesign', save_design_opts)
	pnr_3d_route_tcl.write('')

	if pdflow.is_compact2D_flow():
		# to avoid license problem, we need to use TQuantus instead of IQuantus
		# (from user guide) TQuantus extraction engine is recommended for the implementation phase because it is optimized for performance with a small tradeoff for accuracy. IQuantus extraction engine is recommended for ECO flow, as it has near-signoff accuracy
		# TQuantus: -effortLevel medium
		# IQuantus: -effortLevel high
		extractrcmode_opts = {
			'-effortLevel': 'medium',
			'-engine': 'postRoute',
			'-total_c_th': '0',
			'-relative_c_th': '0.03',
			'-coupling_c_th': '1',
		}
		pnr_3d_route_tcl.write_cmd_w_opts('setExtractRCMode', extractrcmode_opts)

		analysismode_opts = {
			'-analysisType': 'onChipVariation',
			'-cppr': 'both',
		}
		pnr_3d_route_tcl.write_cmd_w_opts('setAnalysisMode', analysismode_opts)

		delaycalmode_opts = {
			'-siAware': 'true',
			'-engine': 'aae',
		}
		pnr_3d_route_tcl.write_cmd_w_opts('setDelayCalMode', delaycalmode_opts)

		placemode_opts = {
			'-allowBorderPinAbut': 'true',
			'-expAdvPinAccess': 'false',
		}
		pnr_3d_route_tcl.write_cmd_w_opts('setPlaceMode', placemode_opts)

		nanoroutemode_opts = {
			'-routeWithViaInPin': 'true',
			'-routeWithViaOnlyForStandardCellPin': 'true',
			'-routeWithEco': 'true',
			'-routeWithSiDriven	': 'true',
			'-routeWithTimingDriven': 'true',
			'-dbAllowInstanceOverlaps': 'false',
			'-routeWithViaOnlyForStandardCellPin': 'true',
		}
		bottom_routing_layer = int(get_dict(FLOW_CFGS, 'TECH_CFG', 'PNR', 'ROUTE', 'BOTTOM_ROUTING_LAYER'))
		if bottom_routing_layer is None:
			bottom_routing_layer = 1
		total_num_route_layer = sum(FLOW_VARS['PNR_3D_NUM_ROUTE_LAYERS'])
		
		if FLOW_ENVS['IMPL_TYPE'] == 'f2b':
			nanoroutemode_opts['-drouteOnGridOnly'] = 'via '+str(bottom_routing_layer)+':'+str(total_num_route_layer)
			pass
		else:
			nanoroutemode_opts['-drouteOnGridOnly'] = 'via '+str(bottom_routing_layer)+':'+str(total_num_route_layer-bottom_routing_layer+1)

		optmode_opts = {
			'-fixHoldAllowSetupTnsDegrade': 'false',
			'-ignorePathGroupsForHold': '{default}',
			'-moveInst': 'true',
			'-addInst': 'true',
			'-addInstancePrefix': 'postPartOpt_',
			'-addNetPrefix': 'postPartOpt_',
			'-deleteInst': 'true',
			'-downsizeInst': 'true',
			'-postRouteAllowOverlap': 'false',
			'-allEndPoints': 'true',
			'-verbose': 'true',
			'-optimizeFF': 'true',
			'-timeDesignExpandedView': 'true',
		}
		pnr_3d_route_tcl.write_cmd_w_opts('setOptMode', optmode_opts)

		pnr_3d_route_tcl.write_section_comment('run post-route optimization')
		opt_design_opts = {
			'-postRoute': None,
			'-setup': None,
			'-outDir': FLOW_ENVS['REPORT_DIR'],
			'-prefix': 'postPartOpt_',
		}
		if is_on(FLOW_VARS, 'PNR_ENABLE_HOLD_FIX'):
			opt_design_opts['-hold'] = None

	route_design_opts = {
		'-globalDetail': None
	}
	pnr_3d_route_tcl.write_cmd_w_opts('routeDesign', route_design_opts)

	if pdflow.is_compact2D_flow():
		pnr_3d_route_tcl.write_cmd_w_opts('optDesign', opt_design_opts)
		pnr_3d_route_tcl.write('foreach rc_corner [all_rc_corners -active] {')
		rcout_opts = {
			'-rc_corner': '$rc_corner',
			'-spef': os.path.join(FLOW_ENVS['RESULT_DIR'], flow_file_utils.join_filename(FLOW_ENVS['BLOCK'], '$rc_corner', 'spef', 'gz'))
		}
		pnr_3d_route_tcl.write_cmd_w_opts('rcOut', rcout_opts)
		pnr_3d_route_tcl.write('}')

	lefdef_ver = get_dict(FLOW_CFGS, 'PROJECT_CFG', 'TOOL', 'INNOVUS', 'LEFDEF_VERSION')
	if lefdef_ver is not None:
		lefdef_ver = 5.8
	pnr_3d_route_tcl.write('set lefDefOutVersion %.1f' % (lefdef_ver))
	defout_opts = {
		'-floorplan': None,
		'-routing': None,
		os.path.join(FLOW_ENVS['RESULT_DIR'], flow_file_utils.join_filename(FLOW_ENVS['BLOCK'], 'def', 'gz')): None,
	}
	pnr_3d_route_tcl.write_cmd_w_opts('defOut', defout_opts)
	pnr_3d_route_tcl.write('saveNetlist %s' % (os.path.join(FLOW_ENVS['RESULT_DIR'], flow_file_utils.join_filename(FLOW_ENVS['BLOCK'], 'v', 'gz'))))

	pdflow_pnr.innovus_end_commands(pnr_3d_route_tcl)
	pnr_3d_route_tcl.close()

	return ret


def main(main_tcl_file: str) -> int:
	'''
	create 3D LEF, 3D GDS, 3D LIB/DB, and 3D init DEF and verilog to perform 3D routing
	(create all the input collaterals in innovus to perform 3D routing)
	write all the scripts to route 3d designs (merged design) in order to determine the locations of 3d vias

	:param main_tcl_files: path to innovus script
	:return: 0 if script is generated successfully. Otherwise, 1
	'''
	ret = 0

	if pdflow.is_3D_design():
		# list all the files required to do 3d routing
		lef_files = pdflow_pnr.get_lef_files()
		pdflow_pnr.pnr_input_collaterals += lef_files
		if pdflow.is_compact2D_flow():
			invs_lefdef2gds_map_file = os.path.join(FLOW_ENVS['WORK_AREA'], 'library', get_dict(FLOW_CFGS, 'TECH_CFG', 'PDK', 'INNOVUS_LEFDEF2GDS_LAYERMAP'))
			starrc_lefdef2gds_map_file = os.path.join(FLOW_ENVS['WORK_AREA'], 'library', get_dict(FLOW_CFGS, 'TECH_CFG', 'PDK', 'STARRC_LEFDEF2GDS_LAYERMAP'))
			pdflow_pnr.pnr_input_collaterals.append(invs_lefdef2gds_map_file)
			pdflow_pnr.pnr_input_collaterals.append(starrc_lefdef2gds_map_file)
			gds_files = pdflow_pnr.lib_db.query(class_name='cell', view_list=['gds'])
			if pdflow.has_memory():
				gds_files += pdflow_pnr.lib_db.query(class_name='memory', view_list=['gds'])
			pdflow_pnr.pnr_input_collaterals += gds_files
		pvts = pdflow_pnr.lib_db.query(all_corners=True)
		for pvt in pvts:
			lib_files = pdflow_pnr.lib_db.query(class_name='cell', view_list=['lib'], corner_list=[pvt])
			if pdflow.has_memory():
				lib_files += pdflow_pnr.lib_db.query(class_name='memory', cell_list=FLOW_VARS['MEMORY_CELLS'], view_list=['db'], corner_list=pvt)
			pdflow_pnr.pnr_input_collaterals += lib_files
		legalize_result_dir = os.path.join(FLOW_ENVS['WORK_AREA'], 'pnr', '3d_legalize', 'results')
		if FLOW_VARS['PNR_PARTITION_METHOD'] != 'cluster':
			part0_def_file = os.path.join(legalize_result_dir, flow_file_utils.join_filename('part0', 'def', 'gz'))
			part1_def_file = os.path.join(legalize_result_dir, flow_file_utils.join_filename('part1', 'def', 'gz'))
			pdflow_pnr.pnr_input_collaterals.append(part0_def_file)
			pdflow_pnr.pnr_input_collaterals.append(part1_def_file)
		elif FLOW_VARS['PNR_PARTITION_METHOD'] == 'cluster':
			part0_def_file = os.path.join(legalize_result_dir, flow_file_utils.join_filename('part0', 'cluster', 'def', 'gz'))
			part1_def_file = os.path.join(legalize_result_dir, flow_file_utils.join_filename('part1', 'cluster', 'def', 'gz'))
			pdflow_pnr.pnr_input_collaterals.append(part0_def_file)
			pdflow_pnr.pnr_input_collaterals.append(part1_def_file)


		flow_log_utils.write_subsubsection_comment(logger, 'check input collaterals')
		ret |= pdflow.check_file_list(pdflow_pnr.pnr_input_collaterals, logger)
		if ret != 0:
			return ret
		pdflow_pnr.pnr_input_collaterals = []

		# create 3d LEF and its related mapping files
		flow_log_utils.write_subsubsection_comment(logger, 'make 3D LEF')
		iLEF = pdflow_lefdef_utils.LEF(lef_files)
		i3DLEF, ilv_layers, maps_2d_to_3d = iLEF.make_3d_lef(FLOW_ENVS['IMPL_TYPE'], FLOW_VARS['PNR_3D_NUM_ROUTE_LAYERS'], [FLOW_VARS['PNR_3D_ILV_SIZE']], [FLOW_VARS['PNR_3D_ILV_SPACING']], True)
		if pdflow.has_memory():
			lef_site = list(i3DLEF.sites.values())[0]
			i3d_m_name = []
			for m_name in FLOW_VARS['MEMORY_CELLS']:
				i3d_m_name.append(m_name + '_T0')
				i3d_m_name.append(m_name + '_T1')
			for macro in i3DLEF.macros.values():
				if macro.name in i3d_m_name:
					macro.width = lef_site.width
					macro.height = lef_site.height
			i3DLEF.write_lef(os.path.join(FLOW_ENVS['RESULT_DIR'], flow_file_utils.join_filename(FLOW_ENVS['BLOCK'], 'lef')))
		else:
			i3DLEF.write_lef(os.path.join(FLOW_ENVS['RESULT_DIR'], flow_file_utils.join_filename(FLOW_ENVS['BLOCK'], 'lef')))
		flow_file_utils.write_json_file(ilv_layers, os.path.join(FLOW_ENVS['RESULT_DIR'], flow_file_utils.join_filename(FLOW_ENVS['BLOCK'], 'ilv_layers', 'json')))
		flow_file_utils.write_json_file(maps_2d_to_3d, os.path.join(FLOW_ENVS['RESULT_DIR'], flow_file_utils.join_filename(FLOW_ENVS['BLOCK'], 'map', 'json')))

		if pdflow.is_compact2D_flow():
			# create 3d cell GDS and its related maping files. it will be used in ext flow
			flow_log_utils.write_subsubsection_comment(logger, 'make 3D cell GDS')
			invs_lefdef2gds_map = pdflow_gds_utils.read_lefdef2gds_map(invs_lefdef2gds_map_file)
			starrc_lefdef2gds_map = pdflow_grd_utils.read_lefdef2gds_map(starrc_lefdef2gds_map_file)
			iGDS = pdflow_gds_utils.GDS()
			iGDS.read_gds(gds_files=gds_files)
			i3DGDS, invs_3d_lefdef2gds_map, starrc_3d_lefdef2gds_map, starrc_3d_lefdef2grd_map = iGDS.make_3d_gds(invs_lefdef2gds_map, starrc_lefdef2gds_map, maps_2d_to_3d, i3DLEF)
			i3DGDS.write_gds(gds_file=os.path.join(FLOW_ENVS['RESULT_DIR'], flow_file_utils.join_filename(FLOW_ENVS['BLOCK'], 'gds')))
			pdflow_gds_utils.write_lefdef2gds_map(os.path.join(FLOW_ENVS['RESULT_DIR'], flow_file_utils.join_filename(FLOW_ENVS['BLOCK'], 'invs_lefdef2gds.map')), invs_3d_lefdef2gds_map)
			pdflow_grd_utils.write_lefdef2gds_map(os.path.join(FLOW_ENVS['RESULT_DIR'], flow_file_utils.join_filename(FLOW_ENVS['BLOCK'], 'starrc_lefdef2gds.map')), starrc_3d_lefdef2gds_map)
			pdflow_grd_utils.write_lefdef2grd_map(os.path.join(FLOW_ENVS['RESULT_DIR'], flow_file_utils.join_filename(FLOW_ENVS['BLOCK'], 'starrc_lefdef2grd.map')), starrc_3d_lefdef2grd_map)

		# create 3d LIB and DB files
		# TODO: need to generate LIB_CCS for EMIR
		flow_log_utils.write_subsubsection_comment(logger, 'make 3D LIB/DB')
		lib_3d_files = {}
		pvts = pdflow_pnr.lib_db.query(all_corners=True)
		for pvt in pvts:
			lib_files = pdflow_pnr.lib_db.query(class_name='cell', view_list=['lib'], corner_list=[pvt])
			lib_pvt_dir = os.path.join(FLOW_ENVS['RESULT_DIR'], 'lib', pvt)
			flow_file_utils.make_dir(lib_pvt_dir)
			lib_3d_files[pvt] = []
			for lib_file in lib_files:
				basename = os.path.basename(lib_file)
				basename_db = gen_db.rename_lib_to_db(basename)

				lib_3d_file = os.path.join(lib_pvt_dir, basename)
				db_3d_file = os.path.join(lib_pvt_dir, basename_db)

				if os.path.exists(lib_3d_file):
					logger.warning('3D LIB file already exists. skip creating it: %s' % (lib_3d_file))
				else:
					lib = liberty_nldm.LibertyNLDM(lib_file)
					lib_3d = lib.make_3d_lib(maps_2d_to_3d['macro'])
					lib_3d.write_lib(lib_3d_file)
				lib_3d_files[pvt].append(lib_3d_file)
				if os.path.exists(db_3d_file):
					logger.warning('3D DB file already exists. skip creating it: %s' % (db_3d_file))
				else:
					gen_db.gen_db(lib_3d_file, db_3d_file, os.path.join(FLOW_ENVS['SCRIPT_DIR'], flow_file_utils.join_filename(basename, 'tcl')))

		# create mmmc file
		if pdflow.is_compact2D_flow():
			mmmc_file = os.path.join(FLOW_ENVS['SCRIPT_DIR'], flow_file_utils.join_filename(FLOW_ENVS['BLOCK'], 'mmmc', 'tcl'))
			qx_tech_files = {}
			qx_root_dir = get_dict(FLOW_CFGS, 'TECH_CFG', 'PDK', '3D', FLOW_ENVS['IMPL_TYPE'].upper(), 'QRC_ROOT_DIR')
			qx_layer_dir = pdflow.get_3d_layer_conf_name()
			for corner in get_dict(FLOW_CFGS, 'TECH_CFG', 'PDK', '3D', FLOW_ENVS['IMPL_TYPE'].upper(), 'QRC').keys():
				qx_file_path = get_dict(FLOW_CFGS, 'TECH_CFG', 'PDK', '3D', FLOW_ENVS['IMPL_TYPE'].upper(), 'QRC', corner)
				qx_tech_file = os.path.join(FLOW_ENVS['WORK_AREA'], 'library', qx_root_dir, qx_layer_dir, qx_file_path)
				qx_tech_files[corner] = qx_tech_file
			pdflow_pnr.write_mmmc(mmmc_file, lib_files_override=lib_3d_files, qx_tech_file_override=qx_tech_files)
		else:
			mmmc_file = None

		flow_log_utils.write_subsubsection_comment(logger, 'generate innovus scripts')
		# create upf file
		upf_file = os.path.join(FLOW_ENVS['SCRIPT_DIR'], flow_file_utils.join_filename(FLOW_ENVS['BLOCK'], 'upf'))
		pdflow_pnr.write_upf(upf_file)

		# create options file
		options_file = os.path.join(FLOW_ENVS['SCRIPT_DIR'], flow_file_utils.join_filename(FLOW_ENVS['BLOCK'], 'options', 'tcl'))
		pdflow_pnr.write_options(options_file, num_route_layer_override=sum(FLOW_VARS['PNR_3D_NUM_ROUTE_LAYERS']))

		# generate 3d design def, verilog
		ipartDEF = pdflow_lefdef_utils.DEF(lef=iLEF)
		ipartDEF.read_def(part0_def_file, exclude_wires=True)
		ipartDEF.read_def(part1_def_file, exclude_wires=True)

		# memory design: making blkgs and site size macro to row spit
		if pdflow.has_memory():
			for part_name, part_info in ipartDEF.designs.items():
				for compo_name, compo_info in part_info.components.items():
					if compo_info.macro.name in FLOW_VARS['MEMORY_CELLS']:
						fblkg = pdflow_lefdef_utils.DEFBlkg(design=part_info)
						fblkg.type = 0
						fblkg_shape = pdflow_lefdef_utils.Shape(shape_type=0)
						fblkg_shape.rect = compo_info.get_shape().rect
						fblkg.shapes.append(fblkg_shape)
						part_info.blockages.append(fblkg)

		i3DDEF = ipartDEF.make_3d_def(FLOW_ENVS['IMPL_TYPE'], i3DLEF, maps_2d_to_3d, ['part0', 'part1'], FLOW_ENVS['BLOCK'], True)
		i3DDEF.designs[FLOW_ENVS['BLOCK']].write_def(os.path.join(FLOW_ENVS['RESULT_DIR'], flow_file_utils.join_filename(FLOW_ENVS['BLOCK'], 'input', 'floorplan', 'def')), floorplan_only=True)
		i3DDEF.designs[FLOW_ENVS['BLOCK']].write_def(os.path.join(FLOW_ENVS['RESULT_DIR'], flow_file_utils.join_filename(FLOW_ENVS['BLOCK'], 'input', 'def')))
		i3DDEF.designs[FLOW_ENVS['BLOCK']].write_verilog(os.path.join(FLOW_ENVS['RESULT_DIR'], flow_file_utils.join_filename(FLOW_ENVS['BLOCK'], 'input', 'v')))

		# generate tcl scripts
		ret |= write_tcl(main_tcl_file, mmmc_file=mmmc_file, cpf_file=None, upf_file=upf_file, options_file=options_file)
		pdflow_pnr.pnr_input_collaterals.append(main_tcl_file)

		return ret
	else:
		logger.error('3d_route stage is not supported in 2d designs')

		return 1
