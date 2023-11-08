import os.path

import pdflow

import ThreeDFD
import hypergraph
import pdflow_pnr
import dontcarecutsize_partitioner

from flow_utils import *
import flow_tcl_utils
import flow_file_utils
import flow_log_utils

import pdflow_lefdef_utils
import fm_partitioner
import kl_partitioner

from flow_var_utils import flow_vars as FLOW_VARS
from flow_env_utils import flow_envs as FLOW_ENVS
from flow_config_utils import flow_cfgs as FLOW_CFGS
logger = flow_log_utils.start_logging()


def write_tcl(filename: str, part_name: str) -> int:
	'''
	write a script to create sessions for partitioned designs

	:param filename: path to innovus script
	:param part_name: name of partitioned design
	:return: 0 if script is generated successfully. Otherwise, 1
	'''
	ret = 0

	pnr_partition_tcl = flow_tcl_utils.TclFile(filename=filename)

	# suppress expected error message
	# **ERROR: (IMPDF-30):	Line 9223: OffMGrid: Via (-16430, -11260) (-16329, -11000) named VIAGEN_1 is not on Manufacturing Grid.
	pnr_partition_tcl.write('set_message -id IMPDF-30 -suppress')

	pdflow_pnr.innovus_start_commands(pnr_partition_tcl, restore_design=False)
	netlist_file = os.path.join(FLOW_ENVS['RESULT_DIR'], flow_file_utils.join_filename(part_name, 'v'))
	pnr_partition_tcl.write('set init_verilog %s' % (netlist_file))
	pdflow_pnr.pnr_input_collaterals.append(netlist_file)

	lef_files = pdflow_pnr.get_lef_files()
	pnr_partition_tcl.write('set init_lef_file %s' % (flow_tcl_utils.get_list(lef_files)))
	pdflow_pnr.pnr_input_collaterals += lef_files

	pwr_net = get_dict(FLOW_VARS, 'DEFAULT_PWR_NET')
	gnd_net = get_dict(FLOW_VARS, 'DEFAULT_GND_NET')
	pnr_partition_tcl.write('set init_pwr_net %s' % (pwr_net))
	pnr_partition_tcl.write('set init_gnd_net %s' % (gnd_net))
	pnr_partition_tcl.write('set init_top_cell %s' % (part_name))
	pnr_partition_tcl.write('init_design')
	pnr_partition_tcl.write('')
	# using -components to resolve IMPDF-30 would alter the width/height of the core area
	part_def_file = os.path.join(FLOW_ENVS['RESULT_DIR'], flow_file_utils.join_filename(part_name, 'def'))
	pnr_partition_tcl.write('defIn %s' % (part_def_file))
	pdflow_pnr.pnr_input_collaterals.append(part_def_file)

	pdflow_pnr.innovus_end_commands(pnr_partition_tcl, design_name=part_name)
	pnr_partition_tcl.close()

	return ret


class create_hyper():
	def __init__(self, type,  key, tolerance, work_dir, partition):
		self.FM = fm_partitioner.fm_partitioner(node_weight_key=key, node_weight_tolerance=tolerance, work_dir=work_dir, partition_file=partition)
		self.KL = kl_partitioner.kl_partitioner(node_weight_key=key, node_weight_tolerance=tolerance, work_dir=work_dir, partition_file=partition)
		self.Test = dontcarecutsize_partitioner.test_partitioner(work_dir=work_dir, partition_file=partition)
		self.cluster = ThreeDFD.force_directed(work_dir=work_dir)
		self.bins = None
		self.type = type
		self.result = None
		self.part_def = None

	def create(self, iDEF):
		if self.type == 'FM' or None:
			self.FM.from_def(iDEF)
			bins = fm_partitioner.get_bins(iDEF, FLOW_VARS['PNR_COMPACT2D_SHRUNK2D_PART_BIN_SIZE'])
			self.bins = bins
			ofp = flow_file_utils.open_wfile('bins', force=True)
			for bin_num, comp_list in enumerate(bins):
				for comp in comp_list:
					ofp.write('%s %d\n' % (comp, bin_num))
			ofp.close()
			return self.FM, self.bins

		elif self.type == 'KL' or None:
			self.KL.from_def(iDEF)
			bins = fm_partitioner.get_bins(iDEF, FLOW_VARS['PNR_COMPACT2D_SHRUNK2D_PART_BIN_SIZE'])
			self.bins = bins
			ofp = flow_file_utils.open_wfile('bins', force=True)
			for bin_num, comp_list in enumerate(bins):
				for comp in comp_list:
					ofp.write('%s %d\n' % (comp, bin_num))
			ofp.close()
			return self.KL, self.bins

		elif self.type == 'test':
			self.Test.from_def(iDEF)
			return self.Test
		elif self.type == '3DFD':
			pass


def main(main_tcl_files: List[str]) -> int:
	'''
	perform design partition
	and write all the scripts to create sessions for partitioned designs

	:param main_tcl_file: path to innovus script
	:return: 0 if script is generated successfully. Otherwise, 1
	'''
	ret = 0

	if pdflow.is_3D_design():
		# get lef files
		lef_files = pdflow_pnr.get_lef_files()
		pdflow_pnr.pnr_input_collaterals += lef_files

		# get def file
		finish_result_dir = os.path.join(FLOW_ENVS['WORK_AREA'], 'pnr', 'finish', 'results')
		def_file = os.path.join(finish_result_dir, flow_file_utils.join_filename(FLOW_ENVS['BLOCK'], 'def', 'gz'))
		pdflow_pnr.pnr_input_collaterals.append(def_file)

		flow_log_utils.write_subsubsection_comment(logger, 'check input collaterals')
		ret |= pdflow.check_file_list(pdflow_pnr.pnr_input_collaterals, logger)
		if ret != 0:
			return ret
		pdflow_pnr.pnr_input_collaterals = []

		# create lef/def objects
		flow_log_utils.write_subsubsection_comment(logger, 'read lef/def')
		iLEF = pdflow_lefdef_utils.LEF(lef_files)
		iDEF = pdflow_lefdef_utils.DEF(def_file, iLEF, exclude_wires=True)

		flow_log_utils.write_subsubsection_comment(logger, 'handle fixed cells')
		fixed_objs = {}
		# assign all clock cells on part1
		if FLOW_VARS['PNR_3D_PLACE_CLK_CELLS_ON_TOP_TIER']:
			clock_pins, clock_comps, clock_nets = iDEF.designs[FLOW_ENVS['BLOCK']].get_clock_pins_components_nets()
			for clock_obj in clock_pins + clock_comps:
				fixed_objs[clock_obj] = 1
			clock_net = []
			for net in clock_nets:
				clock_net.append(net)
			ofp = flow_file_utils.open_wfile('nets.txt', force=True)
			for name in clock_net:
				ofp.write('%s \n' % (name))
			ofp.close()
			logger.info('total %d clock pins and %d clock cells are fixed on tier 1' % (len(clock_pins), len(clock_comps)))
		# assign all ports on part1
		if FLOW_VARS['PNR_3D_PLACE_PORTS_ON_TOP_TIER']:
			for pin_name in iDEF.designs[FLOW_ENVS['BLOCK']].pins.keys():
				fixed_objs[pin_name] = 1
			logger.info('total %d ports are fixed on tier 1' % (len(iDEF.designs[FLOW_ENVS['BLOCK']].pins.keys())))
		# # assign net on part 1 for clustering
		# if FLOW_VARS['PNR_PARTITION_METHOD'] == 'cluster':
		# 	for net_name in iDEF.designs[FLOW_ENVS['BLOCK']].nets.keys():
		# 		fixed_objs[net_name] = 1
		# 	logger.info('total %d nets are fixed on tier 1' % (len(iDEF.designs[FLOW_ENVS['BLOCK']].nets.keys())))

		# assign all components which is in the power pin blockages to the other tier
		pin_blkg_file = os.path.join(finish_result_dir, flow_file_utils.join_filename(FLOW_ENVS['BLOCK'], 'pin', 'blkg'))
		if os.path.exists(pin_blkg_file):
			num_fixed_cells = [0, 0]
			ifp = flow_file_utils.open_rfile(pin_blkg_file)
			for line in ifp:
				blkg_info = line.split()
				blkg_shape = pdflow_lefdef_utils.Shape(shape_type=0)
				blkg_shape.rect = pdflow_lefdef_utils.Rect(llx=round(float(blkg_info[0])*iDEF.designs[FLOW_ENVS['BLOCK']].dbUnits),
														lly=round(float(blkg_info[1])*iDEF.designs[FLOW_ENVS['BLOCK']].dbUnits),
														urx=round(float(blkg_info[2])*iDEF.designs[FLOW_ENVS['BLOCK']].dbUnits),
														ury=round(float(blkg_info[3])*iDEF.designs[FLOW_ENVS['BLOCK']].dbUnits),
														rect_type=int
														)
				blkg_tier = int(blkg_info[4])
				for comp_name, comp_info in iDEF.designs[FLOW_ENVS['BLOCK']].components.items():
					if blkg_shape.is_intersected(comp_info.get_shape()):
						fixed_objs[comp_name] = 1-blkg_tier
						num_fixed_cells[1-blkg_tier] += 1
			ifp.close()
			logger.info('total %d, %d cells blocked by power pins are fixed on tier 0 and 1, respectively' % (num_fixed_cells[0], num_fixed_cells[1]))

		# macro partitioning
		macro_partition_file = os.path.join(FLOW_ENVS['WORK_AREA'], 'pnr', 'init', 'results', 'macro_partition.txt')
		if os.path.exists(macro_partition_file):
			ifp = flow_file_utils.open_rfile(macro_partition_file)
			for line in ifp:
				macro_name, macro_part = line.split()
				part = int(macro_part)
				fixed_objs[macro_name] = part

				macro_blkg_shape = iDEF.designs[FLOW_ENVS['BLOCK']].components[macro_name].get_shape()

				for comp_name, comp_info in iDEF.designs[FLOW_ENVS['BLOCK']].components.items():
					if macro_blkg_shape.is_intersected(comp_info.get_shape()) and comp_name not in fixed_objs.keys():
						fixed_objs[comp_name] = 1-part
			ifp.close()

		ofp = flow_file_utils.open_wfile(os.path.join(FLOW_ENVS['RESULT_DIR'], flow_file_utils.join_filename(FLOW_ENVS['BLOCK'], 'fixed_objs', 'txt')), force=True)
		for fixed_obj, tier_num in fixed_objs.items():
			ofp.write('%s %d\n' % (fixed_obj, tier_num))
		ofp.close()

		# perform partitioning
		flow_log_utils.write_subsubsection_comment(logger, 'perform tier partitioning')
		partition_file = os.path.join(FLOW_ENVS['RESULT_DIR'], flow_file_utils.join_filename(FLOW_ENVS['BLOCK'], FLOW_VARS['PNR_PARTITION_METHOD'], 'part_result.txt'))
		if not os.path.exists(partition_file):
			HP = create_hyper(FLOW_VARS['PNR_PARTITION_METHOD'], 'area', FLOW_VARS['PNR_COMPACT2D_SHRUNK2D_PART_AREA_SKEW'], FLOW_ENVS['RUN_DIR'], partition_file)
			HP.create(iDEF)
			if FLOW_VARS['PNR_PARTITION_METHOD'] == '3DFD':
				result = HP.cluster.run(iDEF, FLOW_VARS['PNR_PARTITION_CLUSTER_SIZE'], FLOW_VARS['PNR_PARTITION_GRAVI_FACTOR'], FLOW_VARS['PNR_PARTITION_REP_FACTOR'], FLOW_VARS['PNR_PARTITION_ATT_FACTOR'], FLOW_VARS['PNR_PARTITION_CLUS_REP'], FLOW_VARS['PNR_PARTITION_CLUS_ATT'], FLOW_VARS['PNR_PARTITION_CEN_FACTOR'], FLOW_VARS['PNR_PARTITION_PERI_FACTOR'], FLOW_VARS['PNR_PARTITION_AREA_FACTOR'], FLOW_VARS['PNR_PARTITION_ITERATION'], FLOW_VARS['PNR_PARTITION_CLUS_ITER'], fixed_objs)
				for clus in HP.cluster.cluster_data.keys():
					for comp, info in iDEF.designs[FLOW_ENVS['BLOCK']].components.items():
						if comp == clus:
							info.loc.x = HP.cluster.cluster_data[clus].props['location'][0]
							info.loc.y = HP.cluster.cluster_data[clus].props['location'][1]
						elif (comp in HP.cluster.cluster_data[clus].component) and (FLOW_VARS['PNR_PARTITION_CLUS_ITER'] > 0):
							i = HP.cluster.cluster_data[clus].component.index(comp)
							info.loc.x = HP.cluster.cluster_data[clus].props['peri_loc'][i][0]
							info.loc.y = HP.cluster.cluster_data[clus].props['peri_loc'][i][1]
						elif (comp in HP.cluster.cluster_data[clus].component) and (FLOW_VARS['PNR_PARTITION_CLUS_ITER'] == 0):
							info.loc.x = HP.cluster.cluster_data[clus].props['location'][0]
							info.loc.y = HP.cluster.cluster_data[clus].props['location'][1]
						else:
							pass
				iDEF.designs[FLOW_ENVS['BLOCK']].write_def(os.path.join(finish_result_dir, flow_file_utils.join_filename('force_directed', 'def')))
				iDEF.designs[FLOW_ENVS['BLOCK']].write_verilog(os.path.join(finish_result_dir, flow_file_utils.join_filename('force_directed', 'v')))
				partdef = iDEF.designs[FLOW_ENVS['BLOCK']].partition_by_pin_comp(partitions=result)

			elif FLOW_VARS['PNR_PARTITION_METHOD'] == 'KL':
				result = HP.KL.run(HP.bins, fixed_objs)
				partdef = iDEF.designs[FLOW_ENVS['BLOCK']].partition_by_pin_comp(partitions=result)

			elif FLOW_VARS['PNR_PARTITION_METHOD'] == 'FM':
				result = HP.FM.run(HP.bins, fixed_objs)
				partdef = iDEF.designs[FLOW_ENVS['BLOCK']].partition_by_pin_comp(partitions=result)
		else:
			# if there is a partition file, just partition design
			partdef = iDEF.designs[FLOW_ENVS['BLOCK']].partition_by_pin_comp(partition_file=partition_file)

		# project/scale design and create def and verilog file
		flow_log_utils.write_subsubsection_comment(logger, 'scale dimension & write outputs')
		for part_name, part_info in partdef.designs.items():
			if FLOW_ENVS['IMPL_METHOD'] == 'compact2d':
				part_info.scale(0.707)
			part_info.write_def(os.path.join(FLOW_ENVS['RESULT_DIR'], flow_file_utils.join_filename(part_name, 'def')))
			part_info.write_verilog(os.path.join(FLOW_ENVS['RESULT_DIR'], flow_file_utils.join_filename(part_name, 'v')))
		if FLOW_VARS['PNR_PARTITION_METHOD'] == '3DFD':
			i3DLEF, ilv_layers, maps_2d_to_3d = iLEF.make_3d_lef(FLOW_ENVS['IMPL_TYPE'], FLOW_VARS['PNR_3D_NUM_ROUTE_LAYERS'], [FLOW_VARS['PNR_3D_ILV_SIZE']], [FLOW_VARS['PNR_3D_ILV_SPACING']], True)
			part_0 = os.path.join(FLOW_ENVS['RESULT_DIR'], flow_file_utils.join_filename('part0', 'def'))
			part_1 = os.path.join(FLOW_ENVS['RESULT_DIR'], flow_file_utils.join_filename('part1', 'def'))
			d_file = os.path.join(finish_result_dir, flow_file_utils.join_filename('force_directed', 'def'))
			cDEF = pdflow_lefdef_utils.DEF(d_file, iLEF, exclude_wires=True)
			cDEF.read_def(part_0, exclude_wires=True)
			cDEF.read_def(part_1, exclude_wires=True)
			i3ddef = cDEF.make_3d_def(FLOW_ENVS['IMPL_TYPE'], i3DLEF, maps_2d_to_3d, ['part0', 'part1'], FLOW_ENVS['BLOCK'], True)
			i3ddef.designs[FLOW_ENVS['BLOCK']].write_def(FLOW_ENVS['RESULT_DIR'], flow_file_utils.join_filename('3d', 'def'))
			maps_3d_to_2d = pdflow_lefdef_utils.convert_maps_2d_to_3d_TO_maps_3d_to_2d(maps_2d_to_3d)
			if pdflow.is_compact2D_flow():
				preserve_wire = True
			else:
				preserve_wire = False
			splitDEF = i3ddef.designs[FLOW_ENVS['BLOCK']].split_by_cutLayer(split_cutLayer_names=ilv_layers, maps_3d_to_2d=maps_3d_to_2d, split_lef=iLEF, row_splitting=True, split_names=['part0', 'part1'], exclude_wires=not preserve_wire)
			for name, info in splitDEF.designs.items():
				info.scale(0.707)
			splitDEF.designs['part0'].write_verilog(os.path.join(FLOW_ENVS['RESULT_DIR'], flow_file_utils.join_filename('part0', 'cluster',  'v')))
			splitDEF.designs['part0'].write_def(os.path.join(FLOW_ENVS['RESULT_DIR'], flow_file_utils.join_filename('part0', 'cluster',  'def')))
			splitDEF.designs['part1'].write_verilog(os.path.join(FLOW_ENVS['RESULT_DIR'], flow_file_utils.join_filename('part1', 'cluster', 'v')))
			splitDEF.designs['part1'].write_def(os.path.join(FLOW_ENVS['RESULT_DIR'], flow_file_utils.join_filename('part1', 'cluster', 'def')))


		# write tcl script to create sessions for designs
		flow_log_utils.write_subsubsection_comment(logger, 'generate innovus scripts')
		for part_tcl_file, part_name in zip(main_tcl_files, list(partdef.designs.keys())):
			ret |= write_tcl(part_tcl_file, part_name)
			pdflow_pnr.pnr_input_collaterals.append(part_tcl_file)

		return ret
	else:
		logger.error('3d_partition stage is not supported in 2d designs')

		return 1

if __name__ == '__main__':
	main_tcl_files = [
		os.path.join(FLOW_ENVS['SCRIPT_DIR'], flow_file_utils.join_filename('part0', 'tcl')),
		os.path.join(FLOW_ENVS['SCRIPT_DIR'], flow_file_utils.join_filename('part1', 'tcl'))
	]
	main(main_tcl_files)
