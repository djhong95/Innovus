import pdflow
import pdflow_pnr

from flow_utils import *
import flow_tcl_utils
import flow_file_utils
import flow_log_utils

from flow_var_utils import flow_vars as FLOW_VARS
from flow_env_utils import flow_envs as FLOW_ENVS

logger = flow_log_utils.start_logging()


def write_tcl(filename: str, mmmc_file: str, cpf_file: Union[str, None], upf_file: Union[str, None], options_file: str) -> int:
	'''
	write a script to perform init stage of pnr

	:param filename: path to pnr script
	:param mmmc_file: path to mmmc file
	:param cpf_file: path to cpf file
	:param upf_file: path to upf file
	:param options_file: path to options file
	:return: 0 if script is generated successfully. Otherwise, 1
	'''
	ret = 0
	pnr_init_tcl = flow_tcl_utils.TclFile(filename=filename)

	pdflow_pnr.innovus_start_commands(pnr_init_tcl, restore_design=False)

	design_mode_opts = {
		'-pessimisticMode': 'true',
	}
	pnr_init_tcl.write_cmd_w_opts('setDesignMode', design_mode_opts)	
	syn_result_dir = os.path.join(os.path.join(FLOW_ENVS['WORK_AREA'], 'syn', 'results'))
	syn_netlist_file = os.path.join(syn_result_dir, flow_file_utils.join_filename(FLOW_ENVS['BLOCK'], 'v'))
	pnr_init_tcl.write('set init_verilog %s' % (syn_netlist_file))
	pdflow_pnr.pnr_input_collaterals.append(syn_netlist_file)

	lef_files = pdflow_pnr.get_lef_files()
	pnr_init_tcl.write('set init_lef_file %s' % (flow_tcl_utils.get_list(lef_files)))
	pdflow_pnr.pnr_input_collaterals += lef_files

	rail_spec = get_dict(FLOW_VARS, 'PNR_FPLAN_RAIL_SPEC')
	bump_size = get_dict(FLOW_VARS, 'PNR_FPLAN_BUMP_SIZE')
	bump_pitch = get_dict(FLOW_VARS, 'PNR_FPLAN_BUMP_PITCH')
	if rail_spec is not None and bump_size is not None and bump_pitch is not None:
		pwr_net = get_dict(FLOW_VARS, 'DEFAULT_PWR_NET')
		gnd_net = get_dict(FLOW_VARS, 'DEFAULT_GND_NET')
		pnr_init_tcl.write('set init_pwr_net %s' % (pwr_net))
		pnr_init_tcl.write('set init_gnd_net %s' % (gnd_net))
	pnr_init_tcl.write('set init_top_cell %s' % (FLOW_ENVS['BLOCK']))
	pnr_init_tcl.write('set init_mmmc_file %s' % (mmmc_file))
	pdflow_pnr.pnr_input_collaterals.append(mmmc_file)
	pnr_init_tcl.write('init_design')
	pnr_init_tcl.write('')
	if rail_spec is not None and bump_size is not None and bump_pitch is not None:
		if upf_file is not None:
			pnr_init_tcl.write('read_power_intent -1801 %s' % (upf_file))
			pdflow_pnr.pnr_input_collaterals.append(upf_file)
		elif cpf_file is not None:
			pnr_init_tcl.write('read_power_intent -cpf %s' % (cpf_file))
			pdflow_pnr.pnr_input_collaterals.append(cpf_file)
		else:
			logger.warning('power intent file does not exist.')
		pnr_init_tcl.write('commit_power_intent')
	pnr_init_tcl.write('')
	pnr_init_tcl.write('source %s' % (options_file))
	pdflow_pnr.pnr_input_collaterals.append(options_file)

	# store verilog & sdf
	pnr_init_tcl.write('saveNetlist %s' % (os.path.join(FLOW_ENVS['RESULT_DIR'], flow_file_utils.join_filename(FLOW_ENVS['BLOCK'], 'v', 'gz'))))
	pnr_init_tcl.write('write_sdf %s' % os.path.join(FLOW_ENVS['RESULT_DIR'], flow_file_utils.join_filename(FLOW_ENVS['BLOCK'], 'sdf')))

	pdflow_pnr.innovus_end_commands(pnr_init_tcl)
	pnr_init_tcl.close()

	return ret


# def overlap_region(R0: (tuple or list), R1: (tuple, list)) -> List[int]:
# 	"""
# 	calculate overlap rectangle
# 	:param: list of point coordinate of two rectangle c.f., (R0.llx, R0.lly, R0.urx, R0.ury) (R1.llx, R1.lly, R1.urx, R1.ury)
#
# 	:return: the point coordinate of overlap rectangle
# 	"""
# 	overlap = []
# 	R0_llx = R0[0]
# 	R0_lly = R0[1]
# 	R0_urx = R0[2]
# 	R0_ury = R0[3]
# 	R1_llx = R1[0]
# 	R1_lly = R1[1]
# 	R1_urx = R1[2]
# 	R1_ury = R1[3]
# 	ov_llx = 0
# 	ov_lly = 0
# 	ov_urx = 0
# 	ov_ury = 0
# 	if R0_llx <= R1_llx <= R0_urx:
# 		if R0_lly >= R1_ury or R0_ury <= R1_lly:
# 			pass
# 		elif R0_lly < R1_ury:
# 			ov_llx = R1_llx
# 			ov_lly = max(R0_lly, R1_lly)
# 			ov_urx = min(R0_urx, R1_urx)
# 			ov_ury = min(R0_ury, R1_ury)
# 	elif R0_llx > R1_llx:
# 		if R0_llx >= R1_urx or R0_lly >= R1_ury or R0_ury <= R1_lly:
# 			pass
# 		elif R0_llx < R1_urx and R0_lly < R1_ury:
# 			ov_llx = R0_llx
# 			ov_lly = R0_lly
# 			ov_urx = min(R0_urx, R1_urx)
# 			ov_ury = min(R0_ury, R1_ury)
# 	elif R0_urx <= R1_llx:
# 		pass
#
# 	if ov_llx != 0:
# 		overlap.append(ov_llx)
# 		overlap.append(ov_lly)
# 		overlap.append(ov_urx)
# 		overlap.append(ov_ury)
#
# 	return overlap
#
#
# def partial_overlap_region(fblkg, macro_R) -> List[int]:
# 	'''
# 	:param fblkg: full blockage region obtained by overlap_region()
# 	:param macro_R: macro region
#
# 	:return: the list of partial blockage regions, the specific region of partial blockage as below
# 	'''
# 	'''
# 	---------------------
# 	|		|	2		|
# 	|		|----------	|
# 	|		|*****|		|
# 	| pov1	|fblkg|	4	|
# 	|		|*****|		|
# 	|		|----------	|
# 	|		|	3		|
# 	---------------------
# 	'''
# 	partial_ovelap = []
# 	fblkg_llx = fblkg[0]
# 	fblkg_lly = fblkg[1]
# 	fblkg_urx = fblkg[2]
# 	fblkg_ury = fblkg[3]
# 	mR_llx = macro_R[0]
# 	mR_lly = macro_R[1]
# 	mR_urx = macro_R[2]
# 	mR_ury = macro_R[3]
# 	pov1 = [0, 0, 0, 0]
# 	pov2 = [0, 0, 0, 0]
# 	pov3 = [0, 0, 0, 0]
# 	pov4 = [0, 0, 0, 0]
#
# 	if mR_llx <= fblkg_llx <= mR_urx:
# 		if mR_lly >= fblkg_ury or mR_ury <= fblkg_lly:
# 			pass
# 		else:
# 			pov1[0] = mR_llx
# 			pov1[1] = mR_lly
# 			pov1[2] = fblkg_llx
# 			pov1[3] = mR_ury
# 			if mR_ury >= fblkg_ury:
# 				pov2[0] = fblkg_llx
# 				pov2[1] = fblkg_ury
# 				pov2[2] = mR_urx
# 				pov2[3] = mR_ury
# 			if mR_lly <= fblkg_lly:
# 				pov3[0] = fblkg_llx
# 				pov3[1] = mR_lly
# 				pov3[2] = mR_urx
# 				pov3[3] = fblkg_lly
# 			if mR_urx >= fblkg_urx:
# 				pov4[0] = fblkg_urx
# 				pov4[1] = fblkg_lly
# 				pov4[2] = mR_urx
# 				pov4[3] = fblkg_ury
# 	elif mR_llx > fblkg_llx:
# 		if mR_llx >= fblkg_urx or mR_lly >= fblkg_ury or mR_ury <= fblkg_lly:
# 			pass
# 		elif mR_llx < fblkg_urx and mR_lly < fblkg_ury:
# 			if mR_lly >= fblkg_lly and mR_ury <= fblkg_ury:
# 				pov4[0] = fblkg_urx
# 				pov4[1] = mR_lly
# 				pov4[2] = mR_urx
# 				pov4[3] = mR_ury
# 			elif mR_lly >= fblkg_lly and mR_ury >= fblkg_ury:
# 				pov2[0] = mR_llx
# 				pov2[1] = fblkg_ury
# 				pov2[2] = mR_urx
# 				pov2[3] = mR_ury
# 				pov4[0] = fblkg_urx
# 				pov4[1] = mR_lly
# 				pov4[2] = mR_urx
# 				pov4[3] = fblkg_ury
# 			elif mR_lly <= fblkg_lly and mR_ury <= fblkg_ury:
# 				pov3[0] = mR_llx
# 				pov3[1] = mR_lly
# 				pov3[2] = mR_urx
# 				pov3[3] = fblkg_lly
# 				pov4[0] = fblkg_urx
# 				pov4[1] = fblkg_lly
# 				pov4[2] = mR_urx
# 				pov4[3] = mR_ury
# 			elif mR_lly < fblkg_lly and mR_ury > fblkg_ury:
# 				pov2[0] = mR_llx
# 				pov2[1] = fblkg_ury
# 				pov2[2] = mR_urx
# 				pov2[3] = mR_ury
# 				pov3[0] = mR_llx
# 				pov3[1] = mR_lly
# 				pov3[2] = mR_urx
# 				pov3[3] = fblkg_lly
# 				pov4[0] = fblkg_urx
# 				pov4[1] = fblkg_lly
# 				pov4[2] = mR_urx
# 				pov4[3] = fblkg_ury
# 	elif mR_urx <= fblkg_llx:
# 		pass
# 	if pov1[0] != 0:
# 		partial_ovelap.append(pov1)
# 	if pov2[0] != 0:
# 		partial_ovelap.append(pov2)
# 	if pov3[0] != 0:
# 		partial_ovelap.append(pov3)
# 	if pov4[0] != 0:
# 		partial_ovelap.append(pov4)
#
# 	return partial_ovelap


def project_def():
	import pdflow_lefdef_utils
	import flow_file_utils

	macro_0_rect = []
	macro_1_rect = []
	partitioning = []
	# read LEF
	lef_files = pdflow_pnr.get_lef_files()
	iLEF = pdflow_lefdef_utils.LEF(lef_files)

	# read DEF
	work_area = os.path.join(FLOW_ENVS['WORK_AREA'])
	part0_def_file = os.path.join(FLOW_VARS['PNR_FPLAN_INIT_DEF'][0])
	part1_def_file = os.path.join(FLOW_VARS['PNR_FPLAN_INIT_DEF'][1])

	part0_DEF = pdflow_lefdef_utils.DEF(def_file=part0_def_file, lef=iLEF, exclude_wires=True)
	part1_DEF = pdflow_lefdef_utils.DEF(def_file=part1_def_file, lef=iLEF, exclude_wires=True)

	# store memory location with absolute point
	for compo_name, compo_info in part0_DEF.designs[FLOW_ENVS['BLOCK']].components.items():
		if compo_info.macro.name in FLOW_VARS['MEMORY_CELLS']:
			m0shape = compo_info.get_shape()
			macro_0_rect.append(m0shape)
			partitioning.append((compo_name, 0))

	for compo_name, compo_info in part1_DEF.designs[FLOW_ENVS['BLOCK']].components.items():
		if compo_info.macro.name in FLOW_VARS['MEMORY_CELLS']:
			m1shape = compo_info.get_shape()
			macro_1_rect.append(m1shape)
			partitioning.append((compo_name, 1))

	macro_rect_list = macro_0_rect + macro_1_rect

	# macro partitioning file writing -> m1 0, m2 1 => it means m1 macro in part0, m2 macro in part1
	ofp = flow_file_utils.open_wfile(os.path.join(FLOW_ENVS['RESULT_DIR'], 'macro_partition.txt'), force=True)
	for macro_part in partitioning:
		ofp.write('%s %d\n' % (macro_part[0], macro_part[1]))
	ofp.close()

	# determine the blockages with full or partial when the both part DEF files are projected into single plane
	full_blkgs = []

	# compute full blockages
	for macro_0 in macro_0_rect:
		for macro_1 in macro_1_rect:
			full_blockage = macro_0.rect.get_intersection(macro_1.rect)
			if full_blockage is not None:
				full_blkgs.append(full_blockage)
	'''
	Partial blockage don't need to be computed. 
	Overlap blockage in innovus is legal.
	We just append the rect.shape of macro as a partial blockage
	'''

	# add blockage in compact2d DEF
	lef_site = list(part0_DEF.LEF.sites.values())[0]
	c2d_DEF = pdflow_lefdef_utils.DEF(lef=iLEF)
	c2d_DEF.read_def(part0_def_file, exclude_wires=True)
	c2d_DEF.read_def(part1_def_file, exclude_wires=True)
	c2d_DEF_design = c2d_DEF.designs[FLOW_ENVS['BLOCK']]

	# full blockage append
	for full_blkg in full_blkgs:
		fblkg = pdflow_lefdef_utils.DEFBlkg(design=c2d_DEF_design)
		fblkg.type = 0
		fblkg_shape = pdflow_lefdef_utils.Shape(shape_type=0)
		fblkg_shape.rect = full_blkg
		fblkg.shapes.append(fblkg_shape)
		c2d_DEF_design.blockages.append(fblkg)

	# partial blockage append
	for partial_blkg in macro_rect_list:
		pblkg = pdflow_lefdef_utils.DEFBlkg(design=c2d_DEF_design)
		pblkg.type = 0
		pblkg.partial = FLOW_VARS['PNR_FPLAN_TARGET_DENSITY'] * 100 / 2
		pblkg_shape = pdflow_lefdef_utils.Shape(shape_type=0)
		pblkg_shape.rect = partial_blkg.rect
		pblkg.shapes.append(pblkg_shape)
		c2d_DEF_design.blockages.append(pblkg)


	for compo_name, compo_info in c2d_DEF_design.components.items():
		if compo_info.macro.name in FLOW_VARS['MEMORY_CELLS']:
			basename = 'shrunk_' + compo_info.macro.name + '.lef'
			if os.path.exists(os.path.join(FLOW_ENVS['WORK_AREA'], basename)):
				pass
			else:
				compo_info.macro.width = lef_site.width
				compo_info.macro.height = lef_site.height
				compo_info.macro.lef.write_lef(lef_file=os.path.join(FLOW_ENVS['WORK_AREA'], basename), only_macro=True)

	# write compact2d floorplan DEF with both full and partial blockages
	c2d_DEF_design.write_def(os.path.join(FLOW_ENVS['RESULT_DIR'], 'c2d.def'))


def main(main_tcl_file: str) -> int:
	'''
	write all the scripts required for init stage of pnr

	:param main_tcl_file: path to pnr script
	:return: 0 if script is generated successfully. Otherwise, 1
	'''
	ret = 0

	mmmc_file = os.path.join(FLOW_ENVS['SCRIPT_DIR'], flow_file_utils.join_filename(FLOW_ENVS['BLOCK'], 'mmmc', 'tcl'))
	#cpf_file = os.path.join(FLOW_ENVS['SCRIPT_DIR'], flow_file_utils.join_filename(FLOW_ENVS['BLOCK'], 'cpf'))
	upf_file = os.path.join(FLOW_ENVS['SCRIPT_DIR'], flow_file_utils.join_filename(FLOW_ENVS['BLOCK'], 'upf'))
	options_file = os.path.join(FLOW_ENVS['SCRIPT_DIR'], flow_file_utils.join_filename(FLOW_ENVS['BLOCK'], 'options', 'tcl'))

	ret |= pdflow_pnr.write_mmmc(mmmc_file)
	rail_spec = get_dict(FLOW_VARS, 'PNR_FPLAN_RAIL_SPEC')
	bump_size = get_dict(FLOW_VARS, 'PNR_FPLAN_BUMP_SIZE')
	bump_pitch = get_dict(FLOW_VARS, 'PNR_FPLAN_BUMP_PITCH')
	if rail_spec is not None and bump_size is not None and bump_pitch is not None:
		#ret |= pdflow.write_cpf(cpf_file)
		ret |= pdflow_pnr.write_upf(upf_file)
	if pdflow.is_3D_design():
		ret |= pdflow_pnr.write_options(options_file, num_route_layer_override=max(FLOW_VARS['PNR_3D_NUM_ROUTE_LAYERS']))
	else:
		ret |= pdflow_pnr.write_options(options_file)

	init_def = get_dict(FLOW_VARS, 'PNR_FPLAN_INIT_DEF')
	if init_def is None:
		pass
	elif FLOW_ENVS['IMPL_TYPE'] != '2d' and len(init_def) >= 2:
		project_def()

	ret |= write_tcl(main_tcl_file, mmmc_file=mmmc_file, cpf_file=None, upf_file=upf_file, options_file=options_file)
	pdflow_pnr.pnr_input_collaterals.append(main_tcl_file)

	return ret
