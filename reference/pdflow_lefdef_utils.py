#!/usr/bin/env python3
import os
import re
from typing import *

import hypergraph
from shapely.geometry import Polygon

from flow_utils import *
import flow_file_utils
import directedgraph
import LEFDEF
import flow_log_utils
import verilog_parse
# from flow_var_utils import flow_vars as FLOW_VARS
import pdflow

logger = flow_log_utils.start_logging()
'''
These classes are just more pythoninc version of LEFDEF parser.
So, if you change something in here, those changes should be also applied to c++ LEFDEF parser.
THEY NEED DO BE ALWAYS SYNCED
'''


#########################################
# From LEFDEF_primitives.hpp
#########################################
class Point:
	"""
	represents point in a design
	"""
	point_type: Type
	'''
	represented with either int or float	
	'''
	x: Union[int, float, None]
	'''
	x location
	'''
	y: Union[int, float, None]
	'''
	y location
	'''
	props: Dict[str, Any]
	'''
	user-defined properties
	'''

	def __init__(self, x: Union[int, float] = None, y: Union[int, float] = None, swig_ref: Union[LEFDEF.intPoint, LEFDEF.doublePoint] = None, point_type: Type = float):
		"""
		create a point

		:param x: x of the point
		:param y: y of the point
		:param swig_ref: imported intPoint from LEFDEF C++ library, if not specified, create empty object
		:param point_type: type of the point (int or float)
		"""
		if swig_ref is not None:
			if isinstance(swig_ref, LEFDEF.intPoint):
				self.point_type = int
				self.x = round(swig_ref.x)
				self.y = round(swig_ref.y)
			else:
				self.point_type = float
				self.x = float(swig_ref.x)
				self.y = float(swig_ref.y)
		elif x is not None and y is not None:
			self.point_type = point_type
			if self.point_type == int:
				self.x = round(x)
				self.y = round(y)
			else:
				self.x = float(x)
				self.y = float(y)
		else:
			self.point_type = point_type
			self.x = None
			self.y = None
		self.props = {}

	def __setitem__(self, key, value):
		self.props[key] = value

	def __getitem__(self, item):
		return self.props[item]

	def __contains__(self, item):
		if item in self.props:
			return True
		else:
			return False

	def export(self) -> Union[LEFDEF.intPoint, LEFDEF.doublePoint]:
		"""
		export the point to LEFDEF C++ library

		:return: intPoint or doublePoint in LEFDEF C++ library
		"""
		if self.point_type == int:
			targ = LEFDEF.intPoint()
			if self.x is not None:
				targ.x = round(self.x)
			if self.y is not None:
				targ.y = round(self.y)
			return targ
		else:
			targ = LEFDEF.doublePoint()
			if self.x is not None:
				targ.x = float(self.x)
			if self.y is not None:
				targ.y = float(self.y)
			return targ

	def copy(self) -> 'Point':
		"""
		copy the object

		:return: copied object
		"""
		cp = Point()
		cp.point_type = self.point_type
		cp.x = self.x
		cp.y = self.y
		cp.props = self.props.copy()
		return cp

	def scale(self, scale_factor: float, snap_spacing: Union[int, float] = None):
		"""
		scale the point by scale_factor.

		:param scale_factor: scale factor (ratio, not percentage) (e.g., if you want to shrink point by 50%, this value should be 0.5)
		:param snap_spacing: after scaling, snap the point to grids with spacing of this value
		"""
		self.x *= scale_factor
		self.y *= scale_factor
		if snap_spacing is not None:
			self.x = round(self.x / snap_spacing) * snap_spacing
			self.y = round(self.y / snap_spacing) * snap_spacing
		if self.point_type == int:
			self.x = round(self.x)
			self.y = round(self.y)

	def MX(self):
		"""
		mirror the point across x axis
		"""
		self.y = -1 * self.y
		if self.point_type == int:
			self.y = round(self.y)

	def MY(self):
		"""
		mirror the point across y axis
		"""
		self.x = -1 * self.x
		if self.point_type == int:
			self.x = round(self.x)

	def R270(self):
		"""
		rotate the point 270 degree counter clock-wise
		"""
		temp = self.x
		self.x = self.y
		self.y = -1 * temp
		if self.point_type == int:
			self.x = round(self.x)
			self.y = round(self.y)

	def R180(self):
		"""
		rotate the point 180 degree counter clock-wise
		"""
		self.x = -1 * self.x
		self.y = -1 * self.y
		if self.point_type == int:
			self.x = round(self.x)
			self.y = round(self.y)

	def R90(self):
		"""
		rotate the point 90 degree counter clock-wise
		"""
		temp = self.x
		self.x = -1 * self.y
		self.y = temp
		if self.point_type == int:
			self.x = round(self.x)
			self.y = round(self.y)

	def move(self, x: Union[int, float], y: Union[int, float]):
		"""
		move the point by 'x' and 'y'

		:param x: x offset
		:param y: y offset
		"""
		self.x = self.x + x
		self.y = self.y + y
		if self.point_type == int:
			self.x = round(self.x)
			self.y = round(self.y)

	def to_integer(self):
		"""
		change the type of point to integer
		"""
		self.point_type = int
		self.x = round(self.x)
		self.y = round(self.y)

	def to_float(self):
		"""
		change the type of point to float
		"""
		self.point_type = float
		self.x = float(self.x)
		self.y = float(self.y)


class Rect:
	"""
	represents a rectangle  in a design
	"""
	rect_type: Type
	'''
	represented with either int or float
	'''
	ll: Union['Point', None]
	'''
	lower-left point of the rectangle
	'''
	ur: Union['Point', None]
	'''
	upper-right point of the rectangle
	'''
	props: Dict[str, Any]
	'''
	user-defined properties
	'''

	def __init__(self, llx: Union[int, float] = None, lly: Union[int, float] = None, urx: Union[int, float] = None, ury: Union[int, float] = None, swig_ref: Union[LEFDEF.intRect, LEFDEF.doubleRect] = None, rect_type: Type = float):
		"""
		create a rectangle with points

		:param llx: llx of the rectangle
		:param lly: lly of the rectangle
		:param urx: urx of the rectangle
		:param ury: ury of the rectangle
		:param swig_ref: imported intRect from LEFDEF C++ library, if not specified, create empty object
		:param rect_type: type of each point (int or float)
		"""
		if swig_ref is not None:
			if isinstance(swig_ref, LEFDEF.intRect):
				self.rect_type = int
			else:
				self.rect_type = float
			self.ll = Point(swig_ref.llx, swig_ref.lly, point_type=self.rect_type)
			self.ur = Point(swig_ref.urx, swig_ref.ury, point_type=self.rect_type)
		elif llx is not None and lly is not None and urx is not None and ury is not None:
			self.rect_type = rect_type
			self.ll = Point(llx, lly, point_type=self.rect_type)
			self.ur = Point(urx, ury, point_type=self.rect_type)
		else:
			self.rect_type = rect_type
			self.ll = None
			self.ur = None
		self.props = {}

	def __setitem__(self, key, value):
		self.props[key] = value

	def __getitem__(self, item):
		return self.props[item]

	def __contains__(self, item):
		if item in self.props:
			return True
		else:
			return False

	def export(self) -> Union[LEFDEF.intRect, LEFDEF.doubleRect]:
		"""
		export the rectangle to LEFDEF C++ library

		:return: intRect or doubleRect in LEFDEF C++ library
		"""
		if self.rect_type == int:
			targ = LEFDEF.intRect()
			targ.llx = round(self.ll.x)
			targ.lly = round(self.ll.y)
			targ.urx = round(self.ur.x)
			targ.ury = round(self.ur.y)
			return targ
		else:
			targ = LEFDEF.doubleRect()
			targ.llx = float(self.ll.x)
			targ.lly = float(self.ll.y)
			targ.urx = float(self.ur.x)
			targ.ury = float(self.ur.y)
			return targ

	def copy(self) -> 'Rect':
		"""
		copy the object

		:return: copied object
		"""
		cp = Rect()
		cp.rect_type = self.rect_type
		cp.ll = self.ll.copy()
		cp.ur = self.ur.copy()
		cp.props = self.props.copy()
		return cp

	def scale(self, scale_factor: float, snap_spacing: Union[int, float] = None):
		"""
		scale the rectangle by scale_factor.

		:param scale_factor: scale factor (ratio, not percentage) (e.g., if you want to shrink rectangle by 50%, this value should be 0.5)
		:param snap_spacing: after scaling, snap the point to grids with spacing of this value
		"""
		self.ll.scale(scale_factor, snap_spacing=snap_spacing)
		self.ur.scale(scale_factor, snap_spacing=snap_spacing)

	def update_ll_ur(self):
		"""
		keep llx < urx, lly < ury
		"""
		if self.ll.x > self.ur.x:
			temp = self.ll.x
			self.ll.x = self.ur.x
			self.ur.x = temp
		if self.ll.y > self.ur.y:
			temp = self.ll.y
			self.ll.y = self.ur.y
			self.ur.y = temp

	def MX(self):
		"""
		mirror the rectangle across x axis
		"""
		self.ll.MX()
		self.ur.MX()
		self.update_ll_ur()

	def MY(self):
		"""
		mirror the rectangle across y axis
		"""
		self.ll.MY()
		self.ur.MY()
		self.update_ll_ur()

	def R270(self):
		"""
		rotate the rectangle 270 degree counter clock-wise
		"""
		self.ll.R270()
		self.ur.R270()
		self.update_ll_ur()

	def R180(self):
		"""
		rotate the rectangle 180 degree counter clock-wise
		"""
		self.ll.R180()
		self.ur.R180()
		self.update_ll_ur()

	def R90(self):
		"""
		rotate the rectangle 90 degree counter clock-wise
		"""
		self.ll.R90()
		self.ur.R90()
		self.update_ll_ur()

	def move(self, x: int, y: int):
		"""
		move the rectangle by 'x' and 'y'

		:param x: x offset
		:param y: y offset
		"""
		self.ll.move(x, y)
		self.ur.move(x, y)
		self.update_ll_ur()

	def to_integer(self):
		"""
		change the type of rect to integer
		"""
		self.rect_type = int
		self.ll.to_integer()
		self.ur.to_integer()

	def to_float(self):
		"""
		change the type of rect to float
		"""
		self.rect_type = float
		self.ll.to_float()
		self.ur.to_float()

	def get_intersection(self, other: 'Rect') -> Union['Rect', None]:
		"""
		get the intersection between this rectangle and the given rectangle (other)

		:param other: rectangle that will be used to get intersection with this rectangle
		:return: rectangle which represents the intersection of two rectangle, if there is no intersection, return None.
		"""
		intersection_llx = max(self.ll.x, other.ll.x)
		intersection_lly = max(self.ll.y, other.ll.y)
		intersection_urx = min(self.ur.x, other.ur.x)
		intersection_ury = min(self.ur.y, other.ur.y)
		if intersection_llx >= intersection_urx:
			return None
		elif intersection_lly >= intersection_ury:
			return None
		intersection = Rect(intersection_llx, intersection_lly, intersection_urx, intersection_ury, rect_type=self.rect_type)
		return intersection

	def is_in(self, other: 'Rect') -> bool:
		"""
		check whether this rectangle is completely in the given rectangle (other)

		:param other: rectangle that will be used to check
		:return: True if this rectangle is completely in other. otherwise, False
		"""
		if other.ll.x <= self.ll.x and self.ur.x <= other.ur.x and other.ll.y <= self.ll.y and self.ur.y <= other.ur.y:
			return True
		else:
			return False


class Shape:
	"""
	represents a shape in a design
	"""
	shape_type: int
	'''
	represent shape type
	-1: NULL
	0: intRect
	1: doubleRect
	2: iPolygon
	3: dPolygon	
	'''
	layer: Union['LEFLayer', None]
	'''
	LEF layer that this shape lies on
	'''
	rect: Union['Rect', None]
	'''
	rectangle shape
	'''
	polygon: List['Point']
	'''
	polygon shape
	'''
	props: Dict[str, Any]
	'''
	user-defined properties
	'''

	def __init__(self, swig_ref: LEFDEF.Shape = None, layers: Dict[str, 'LEFLayer'] = None, shape_type: int = -1):
		"""
		create a shape

		:param swig_ref: imported Shape from LEFDEF C++ library, if not specified, create empty object
		:param layers: full list of LEF layers
		"""
		if swig_ref is None:
			self.shape_type = shape_type
			self.layer = None
			self.rect = None
			self.polygon = []
		else:
			self.shape_type = swig_ref.shapeType
			if layers is not None:
				self.layer = layers[swig_ref.layer_name] if swig_ref.layer_name in layers else None
			else:
				self.layer = None

			self.rect = None
			self.polygon = []
			if self.shape_type == 0:
				self.rect = Rect(swig_ref=swig_ref.iRect)
			elif self.shape_type == 1:
				self.rect = Rect(swig_ref=swig_ref.dRect)
			elif self.shape_type == 2:
				self.polygon = [Point(swig_ref=pt) for pt in list(swig_ref.iPolygon)]
			else:
				self.polygon = [Point(swig_ref=pt) for pt in list(swig_ref.dPolygon)]
		self.props = {}

	def __setitem__(self, key, value):
		self.props[key] = value

	def __getitem__(self, item):
		return self.props[item]

	def __contains__(self, item):
		if item in self.props:
			return True
		else:
			return False

	def export(self) -> LEFDEF.Shape:
		"""
		export the shape to LEFDEF C++ library

		:return: Shape in LEFDEF C++ library
		"""
		targ = LEFDEF.Shape()
		targ.shapeType = self.shape_type
		targ.layer_name = self.layer.name if self.layer is not None else ''
		targ.iRect = LEFDEF.intRect()
		targ.dRect = LEFDEF.doubleRect()
		targ.iPolygon = LEFDEF.VecIntPt([])
		targ.dPolygon = LEFDEF.VecDoublePt([])
		if self.shape_type == 0 and self.rect is not None:
			targ.iRect = self.rect.export()
		elif self.shape_type == 1 and self.rect is not None:
			targ.dRect = self.rect.export()
		elif self.shape_type == 2:
			targ.iPolygon = LEFDEF.VecIntPt([pt.export() for pt in self.polygon])
		else:
			targ.dPolygon = LEFDEF.VecDoublePt([pt.export() for pt in self.polygon])
		return targ

	def copy(self, layers: Dict[str, 'LEFLayer']) -> 'Shape':
		"""
		copy the object

		:param layers: full list of LEF layers
		:return: copied object
		"""
		cp = Shape()
		cp.shape_type = self.shape_type
		cp.layer = layers[self.layer.name] if self.layer is not None and self.layer.name in layers else None
		cp.rect = self.rect.copy() if self.rect is not None else None
		cp.polygon = [pt.copy() for pt in self.polygon]
		cp.props = self.props.copy()
		return cp

	def scale(self, scale_factor: float, snap_spacing: Union[int, float] = None):
		"""
		scale the shape by scale_factor.

		:param scale_factor: scale factor (ratio, not percentage) (e.g., if you want to shrink shape by 50%, this value should be 0.5)
		:param snap_spacing: after scaling, snap the point to grids with spacing of this value
		"""
		self.rect.scale(scale_factor, snap_spacing=snap_spacing) if self.rect is not None else None
		for pt in self.polygon:
			pt.scale(scale_factor, snap_spacing=snap_spacing)

	def MX(self):
		"""
		mirror the shape across x axis
		"""
		self.rect.MX() if self.rect is not None else None
		for pt in self.polygon:
			pt.MX()

	def MY(self):
		"""
		mirror the shape across y axis
		"""
		self.rect.MY() if self.rect is not None else None
		for pt in self.polygon:
			pt.MY()

	def R270(self):
		"""
		rotate the shape 270 degree counter clock-wise
		"""
		self.rect.R270() if self.rect is not None else None
		for pt in self.polygon:
			pt.R270()

	def R180(self):
		"""
		rotate the shape 180 degree counter clock-wise
		"""
		self.rect.R180() if self.rect is not None else None
		for pt in self.polygon:
			pt.R180()

	def R90(self):
		"""
		rotate the shape 90 degree counter clock-wise
		"""
		self.rect.R90() if self.rect is not None else None
		for pt in self.polygon:
			pt.R90()

	def move(self, x: Union[int, float], y: Union[int, float]):
		"""
		move the shape by 'x' and 'y'

		:param x: x offset
		:param y: y offset
		"""
		self.rect.move(x, y) if self.rect is not None else None
		for pt in self.polygon:
			pt.move(x, y)

	def to_integer(self):
		"""
		change the type of shape to integer
		"""
		if self.shape_type == 1 or self.shape_type == 3:
			self.shape_type -= 1
			self.rect.to_integer() if self.rect is not None else None
			for pt in self.polygon:
				pt.to_integer()

	def to_float(self):
		"""
		change the type of shape to float
		"""
		if self.shape_type == 0 or self.shape_type == 2:
			self.shape_type += 1
			self.rect.to_float() if self.rect is not None else None
			for pt in self.polygon:
				pt.to_float()

	def change_layers(self, layer_map: Dict[str, str], new_layers: Dict[str, 'LEFLayer']):
		'''
		change LEF layer based on layer_map. the resulting shapes will point layers in layers

		:param layer_map: current layer name:new layer name map
		:param new_layers: dict of layer name to LEFLayer object for all new layers
		'''
		self.layer = new_layers[layer_map[self.layer.name]] if self.layer is not None and self.layer.name in layer_map and layer_map[self.layer.name] in new_layers else None

	def get_polygon(self) -> Union[Polygon, None]:
		if self.shape_type == 0 or self.shape_type == 1:
			return Polygon([(self.rect.ll.x, self.rect.ll.y), (self.rect.ur.x, self.rect.ll.y), (self.rect.ur.x, self.rect.ur.y), (self.rect.ll.x, self.rect.ur.y)])
		elif self.shape_type == 2 or self.shape_type == 3:
			return Polygon([(pt.x, pt.y) for pt in self.polygon])
		else:
			logger.error('unknown shape type %d' % (self.shape_type))
			return None

	def is_intersected(self, other: 'Shape') -> bool:
		if (self.layer is None and other.layer is None) or (self.layer.name == other.layer.name):
			self_polygon = self.get_polygon()
			targ_polygon = other.get_polygon()
			if self_polygon.intersects(targ_polygon):
				return True
		return False


#########################################
# From LEF.hpp
#########################################
class LEFTable:
	"""
	represent two dimensional tables in LEF
	"""
	row_idx: List[float]
	''' 
	row index of the table
	'''
	column_idx: List[float]
	'''
	column index of the table
	'''
	values: List[List[float]]
	'''
	values of the table
	'''
	props: Dict[str, Any]
	'''
	user-defined properties
	'''

	def __init__(self, swig_ref: LEFDEF.LEFTable = None):
		"""
		create a LEF Table

		:param swig_ref: imported LEFTable from LEFDEF C++ library, if not specified, create empty object
		"""
		if swig_ref is None:
			self.row_idx = []
			self.column_idx = []
			self.values = []
		else:
			self.row_idx = list(swig_ref.first_idx)
			self.column_idx = list(swig_ref.second_idx)
			self.values = [list(row) for row in list(swig_ref.table)]
		self.props = {}

	def __setitem__(self, key, value):
		self.props[key] = value

	def __getitem__(self, item):
		return self.props[item]

	def __contains__(self, item):
		for item in self.props:
			return True
		else:
			return False

	def export(self) -> LEFDEF.LEFTable:
		"""
		export the LEF table to LEFDEF C++ library

		:return: LEFTable in LEFDEF C++ library
		"""
		targ = LEFDEF.LEFTable()
		targ.first_idx = LEFDEF.VecDouble(self.row_idx)
		targ.second_idx = LEFDEF.VecDouble(self.column_idx)
		targ.table = LEFDEF.VecVecDouble()
		for row in self.values:
			targ.table.push_back(row)
		return targ

	def copy(self) -> 'LEFTable':
		"""
		copy the object

		:return: copied object
		"""
		cp = LEFTable()
		cp.row_idx = self.row_idx[:]
		cp.column_idx = self.column_idx[:]
		for row in self.values:
			cp.values.append(row[:])
		cp.props = self.props.copy()
		return cp


class LEFLayer:
	"""
	represent a layer in LEF
	"""
	name: str
	'''
	name of the layer
	'''
	lef: Union['LEF', None]
	'''
	lef which this layer is defined
	'''
	id: int
	'''
	layer ID (used to find the order of LEF layers)
	'''
	type: int
	'''
	layer type
	-1: NULL
	0: masterslice
	1: implant
	2: routing
	3: cut
	4: overlap
	'''

	# common
	width: float
	'''
	width of the layer
	'''
	spacing: float
	'''
	spacing of the layer
	'''
	spacing_tables: List['LEFTable']
	'''
	list of spacing tables in the layer
	'''

	# routing
	direction: int
	'''
	for routing layers, direction of the layer
	-1: NULL
	0: horizontal
	1: vertical
	2: diagonal 45
	3: diagonal 135
	'''
	min_area: float
	'''
	for routing layers, min-area of the layer
	'''
	pitch: List[float]
	'''
	for routing layers, pitch of the layer. if given a single value, it represents both x, y pitch. if given two values, they represent x, y pitch respectively
	'''
	min_width: float
	'''
	for routing layers, min-width of the layer
	'''
	offset: List[float]
	'''
	for routing layers, offset of the layer. if given a single value, it represents both x, y offset. if given two values, they represent x, y offset respectively
	'''
	thickness: float
	'''
	for routing layers, thickness of the layer
	'''
	props: Dict[str, Any]
	'''
	user-defined properties
	'''

	def __init__(self, swig_ref: LEFDEF.LEFLayer = None, lef: 'LEF' = None):
		'''
		create a LEF layer

		:param swig_ref: imported LEFLayer from LEFDEF C++ library, if not specified, create empty object
		'''
		if swig_ref is None:
			self.name = ''
			self.lef = None
			self.id = -1
			self.type = -1

			self.width = -1
			self.spacing = -1
			self.spacing_tables = []

			self.direction = -1
			self.min_area = -1
			self.pitch = []
			self.min_width = -1
			self.offset = []
			self.thickness = -1
		else:
			self.name = swig_ref.name
			self.lef = lef
			self.id = swig_ref.id
			self.type = swig_ref.type

			self.width = swig_ref.width
			self.spacing = swig_ref.spacing
			self.spacing_tables = [LEFTable(table) for table in list(swig_ref.spacingTables)]

			self.direction = swig_ref.direction
			self.min_area = swig_ref.minArea
			self.pitch = list(swig_ref.pitch)
			self.min_width = swig_ref.minWidth
			self.offset = list(swig_ref.offset)
			self.thickness = swig_ref.thickness
		self.props = {}

	def __setitem__(self, key, value):
		self.props[key] = value

	def __getitem__(self, item):
		return self.props[item]

	def __contains__(self, item):
		if item in self.props:
			return True
		else:
			return False

	def export(self) -> LEFDEF.LEFLayer:
		"""
		export the LEF layer to LEFDEF C++ library

		:return: LEFLayer in LEFDEF C++ library
		"""
		targ = LEFDEF.LEFLayer()
		targ.name = self.name
		targ.id = self.id
		targ.type = self.type

		targ.width = self.width
		targ.spacing = self.spacing
		targ.spacingTables = LEFDEF.VecLEFTable([table.export() for table in self.spacing_tables])

		targ.direction = self.direction
		targ.minArea = self.min_area
		targ.pitch = LEFDEF.VecDouble(self.pitch)
		targ.minWidth = self.min_width
		targ.offset = LEFDEF.VecDouble(self.offset)
		targ.thickness = self.thickness
		return targ

	def copy(self, lef: 'LEF') -> 'LEFLayer':
		"""
		copy the object

		:return: copied object
		"""
		cp = LEFLayer()
		cp.name = self.name
		cp.lef = lef
		cp.id = self.id
		cp.type = self.type

		cp.width = self.width
		cp.spacing = self.spacing
		cp.spacing_tables = [table.copy() for table in self.spacing_tables]

		cp.direction = self.direction
		cp.min_area = self.min_area
		cp.pitch = self.pitch[:]
		cp.min_width = self.min_width
		cp.offset = self.offset[:]
		cp.thickness = self.thickness
		cp.props = self.props.copy()
		return cp


class LEFVia:
	"""
	represents a LEF via
	"""
	name: str
	'''
	name of the via
	'''
	lef: Union['LEF', None]
	'''
	lef which this layer is defined
	'''
	isDefault: bool
	'''
	whether it is default via or not
	'''
	cutLayer: Union['LEFLayer', None]
	'''
	cut layer of the via
	'''
	botRoutingLayer: Union['LEFLayer', None]
	'''
	bottom routing layer of the via
	'''
	topRoutingLayer: Union['LEFLayer', None]
	'''
	top routing layer of the via
	'''
	cutShapes: List['Shape']
	'''
	cut layer shapes of the via
	'''
	botRoutingShapes: List['Shape']
	'''
	bottom routing layer shape of the via
	'''
	topRoutingShapes: List['Shape']
	'''
	top routing layer shape of the via
	'''
	props: Dict[str, Any]
	'''
	user-defined properties
	'''

	def __init__(self, swig_ref: LEFDEF.LEFVia = None, lef: Union['LEF', 'LEFNonDefaultRule'] = None):
		"""
		create a LEF via

		:param swig_ref: imported LEF via from LEFDEF C++ library, if not specified, create empty object
		:param lef: LEF with LEF layers defined
		"""
		if swig_ref is None:
			self.name = ''
			self.lef = None

			self.isDefault = False

			self.cutLayer = None
			self.botRoutingLayer = None
			self.topRoutingLayer = None

			self.cutShapes = []
			self.botRoutingShapes = []
			self.topRoutingShapes = []
		else:
			self.name = swig_ref.name
			self.isDefault = swig_ref.isDefault

			if lef is not None:
				self.lef = lef
				self.cutLayer = lef.layers[swig_ref.cutLayer_name] if swig_ref.cutLayer_name in lef.layers else None
				self.botRoutingLayer = lef.layers[swig_ref.botRoutingLayer_name] if swig_ref.botRoutingLayer_name in lef.layers else None
				self.topRoutingLayer = lef.layers[swig_ref.topRoutingLayer_name] if swig_ref.topRoutingLayer_name in lef.layers else None

				self.cutShapes = [Shape(swig_ref=shape, layers=lef.layers) for shape in list(swig_ref.cutShapes)]
				self.botRoutingShapes = [Shape(swig_ref=shape, layers=lef.layers) for shape in list(swig_ref.botRoutingShapes)]
				self.topRoutingShapes = [Shape(swig_ref=shape, layers=lef.layers) for shape in list(swig_ref.topRoutingShapes)]
			else:
				self.lef = None
				self.cutLayer = None
				self.botRoutingLayer = None
				self.topRoutingLayer = None

				self.cutShapes = [Shape(swig_ref=shape) for shape in list(swig_ref.cutShapes)]
				self.botRoutingShapes = [Shape(swig_ref=shape) for shape in list(swig_ref.botRoutingShapes)]
				self.topRoutingShapes = [Shape(swig_ref=shape) for shape in list(swig_ref.topRoutingShapes)]
		self.props = {}

	def __setitem__(self, key, value):
		self.props[key] = value

	def __getitem__(self, item):
		return self.props[item]

	def __contains__(self, item):
		if item in self.props:
			return True
		else:
			return False

	def export(self) -> LEFDEF.LEFVia:
		'''
		export the LEF via to LEFDEF C++ library

		:return: LEFVia in LEFDEF C++ library
		'''
		targ = LEFDEF.LEFVia()
		targ.name = self.name
		targ.isDefault = self.isDefault

		targ.cutLayer_name = self.cutLayer.name if self.cutLayer is not None else ''
		targ.botRoutingLayer_name = self.botRoutingLayer.name if self.botRoutingLayer is not None else ''
		targ.topRoutingLayer_name = self.topRoutingLayer.name if self.topRoutingLayer is not None else ''

		targ.cutShapes = LEFDEF.VecShape([shape.export() for shape in self.cutShapes])
		targ.botRoutingShapes = LEFDEF.VecShape([shape.export() for shape in self.botRoutingShapes])
		targ.topRoutingShapes = LEFDEF.VecShape([shape.export() for shape in self.topRoutingShapes])
		return targ

	def copy(self, lef: Union['LEF', 'LEFNonDefaultRule']) -> 'LEFVia':
		'''
		copy the object

		:param lef: LEF with LEF layers defined
		:return: copied object
		'''
		cp = LEFVia()
		cp.name = self.name
		cp.lef = lef
		cp.isDefault = self.isDefault

		cp.cutLayer = lef.layers[self.cutLayer.name] if self.cutLayer is not None and self.cutLayer.name in lef.layers else None
		cp.botRoutingLayer = lef.layers[self.botRoutingLayer.name] if self.botRoutingLayer is not None and self.botRoutingLayer.name in lef.layers else None
		cp.topRoutingLayer = lef.layers[self.topRoutingLayer.name] if self.topRoutingLayer is not None and self.topRoutingLayer.name in lef.layers else None

		cp.cutShapes = [shape.copy(lef.layers) for shape in self.cutShapes]
		cp.botRoutingShapes = [shape.copy(lef.layers) for shape in self.botRoutingShapes]
		cp.topRoutingShapes = [shape.copy(lef.layers) for shape in self.topRoutingShapes]
		return cp

	def change_layer(self, layer_map: Dict[str, str], new_lef: Union['LEF', 'LEFNonDefaultRule']):
		'''
		change LEF layer based on layer_map. the resulting via will point layers in new_LEF

		:param layer_map: current layer name:new layer name map
		:param new_lef: LEF object which contains all the new layers
		'''
		self.cutLayer = new_lef.layers[layer_map[self.cutLayer.name]] if self.cutLayer is not None and self.cutLayer.name in layer_map and layer_map[self.cutLayer.name] in new_lef.layers else None
		self.botRoutingLayer = new_lef.layers[layer_map[self.botRoutingLayer.name]] if self.botRoutingLayer is not None and self.botRoutingLayer.name in layer_map and layer_map[self.botRoutingLayer.name] in new_lef.layers else None
		self.topRoutingLayer = new_lef.layers[layer_map[self.topRoutingLayer.name]] if self.topRoutingLayer is not None and self.topRoutingLayer.name in layer_map and layer_map[self.topRoutingLayer.name] in new_lef.layers else None

		for shape in self.cutShapes:
			shape.change_layers(layer_map, new_lef.layers)
		for shape in self.botRoutingShapes:
			shape.change_layers(layer_map, new_lef.layers)
		for shape in self.topRoutingShapes:
			shape.change_layers(layer_map, new_lef.layers)


class LEFViaRuleLayer:
	"""
	represents layers in via rules in LEF
	"""
	layer: Union['LEFLayer', None]
	'''
	layer specified in its via rule
	'''
	direction: int
	'''
	direction of the layer in its via rule
	-1: NULL
	0: horizontal
	1: vertical
	2: diagonal 45
	3: diagonal 135
	'''
	enclosure: List[float]
	'''
	enclosure of the layer. two values, width and height of the enclosure
	'''
	width: List[float]
	'''
	width of the layer in its via rule
	'''
	spacing: List[float]
	'''
	spacing of the layer in its via rule
	'''
	shapes: List['Shape']
	'''
	list of shapes of the layer in its via rule
	'''
	props: Dict[str, Any]
	'''
	user-defined properties
	'''

	def __init__(self, swig_ref: LEFDEF.LEFViaRuleLayer = None, lef: Union['LEF', 'LEFNonDefaultRule'] = None):
		"""
		create a layer in a via rule

		:param swig_ref: imported LEFViaRuleLayer from LEFDEF C++ library. if not specified, create empty object
		:param lef: LEF with LEF layers defined
		"""
		if swig_ref is None:
			self.layer = None
			self.direction = -1
			self.enclosure = []
			self.width = []
			self.spacing = []
			self.shapes = []
		else:
			if lef is not None:
				self.layer = lef.layers[swig_ref.layer_name]
			else:
				self.layer = None
			self.direction = swig_ref.direction
			self.enclosure = list(swig_ref.enclosure)
			self.width = list(swig_ref.width)
			self.spacing = list(swig_ref.spacing)
			if lef is not None:
				self.shapes = [Shape(swig_ref=shape, layers=lef.layers) for shape in list(swig_ref.shapes)]
			else:
				self.shapes = [Shape(swig_ref=shape) for shape in list(swig_ref.shapes)]
		self.props = {}

	def __setitem__(self, key, value):
		self.props[key] = value

	def __getitem__(self, item):
		return self.props[item]

	def __contains__(self, item):
		if item in self.props:
			return True
		else:
			return False

	def export(self) -> LEFDEF.LEFViaRuleLayer:
		"""
		export the layer in its via rule to LEFDEF C++ library

		:return: LEFViaRuleLayer in LEFDEF C++ library
		"""
		targ = LEFDEF.LEFViaRuleLayer()
		targ.layer_name = self.layer.name if self.layer is not None else ''
		targ.direction = self.direction
		targ.enclosure = LEFDEF.VecDouble(self.enclosure)
		targ.width = LEFDEF.VecDouble(self.width)
		targ.spacing = LEFDEF.VecDouble(self.spacing)
		targ.shapes = LEFDEF.VecShape([shape.export() for shape in self.shapes])
		return targ

	def copy(self, lef: Union['LEF', 'LEFNonDefaultRule']) -> 'LEFViaRuleLayer':
		"""
		copy the object

		:param lef: LEF with LEF layers defined
		:return: copied object
		"""
		cp = LEFViaRuleLayer()
		cp.layer = lef.layers[self.layer.name] if self.layer is not None and self.layer.name in lef.layers else None
		cp.direction = self.direction
		cp.enclosure = self.enclosure[:]
		cp.width = self.width[:]
		cp.spacing = self.spacing[:]
		cp.shapes = [shape.copy(lef.layers) for shape in self.shapes]
		return cp

	def change_layer(self, layer_map: Dict[str, str], new_lef: Union['LEF', 'LEFNonDefaultRule']):
		"""
		change LEF layer based on layer_map. the resulting viarule layer will point layers in new_lef

		:param layer_map: current layer name:new layer name map
		:param new_lef: LEF object which contains all the new layers
		"""
		self.layer = new_lef.layers[layer_map[self.layer.name]] if self.layer is not None and self.layer.name in layer_map and layer_map[self.layer.name] in new_lef.layers else None
		for shape in self.shapes:
			shape.change_layers(layer_map, new_lef.layers)


class LEFViaRule:
	"""
	represent via rules in LEF
	"""
	name: str
	'''
	name of the via rule
	'''
	lef: Union['LEF', None]
	'''
	lef which this layer is defined
	'''
	isGenerate: bool
	'''
	whether it is for generate or not
	'''
	isDefault: bool
	'''
	whether it is default or not
	'''
	cutLayerRule: Union['LEFViaRuleLayer', None]
	'''
	cut layer of the via rule
	'''
	botRoutingLayerRule: Union['LEFViaRuleLayer', None]
	'''
	bottom routing layer of the via rule
	'''
	topRoutingLayerRule: Union['LEFViaRuleLayer', None]
	'''
	top routing layer of the via rule
	'''
	vias: List['LEFVia']
	'''
	vias in this via rule
	'''
	props: Dict[str, Any]
	'''
	user-defined properties
	'''

	def __init__(self, swig_ref: LEFDEF.LEFViaRule = None, lef: 'LEF' = None):
		"""
		create a LEF via rule

		:param swig_ref: imported LEF via rule from LEFDEF C++ library, if not specified, create empty object
		:param lef: LEF with LEF layers defined
		"""
		if swig_ref is None:
			self.name = ''
			self.lef = None
			self.isGenerate = False
			self.isDefault = False

			self.cutLayerRule = None
			self.botRoutingLayerRule = None
			self.topRoutingLayerRule = None
			self.vias = []
		else:
			self.name = swig_ref.name
			self.isGenerate = swig_ref.isGenerate
			self.isDefault = swig_ref.isDefault

			if lef is not None:
				self.lef = lef
				self.cutLayerRule = LEFViaRuleLayer(swig_ref=swig_ref.cutLayerRule, lef=lef)
				self.botRoutingLayerRule = LEFViaRuleLayer(swig_ref=swig_ref.botRoutingLayerRule, lef=lef)
				self.topRoutingLayerRule = LEFViaRuleLayer(swig_ref=swig_ref.topRoutingLayerRule, lef=lef)
				self.vias = [lef.vias[via_name] for via_name in list(swig_ref.via_names)]
			else:
				self.lef = None
				self.cutLayerRule = LEFViaRuleLayer(swig_ref=swig_ref.cutLayerRule)
				self.botRoutingLayerRule = LEFViaRuleLayer(swig_ref=swig_ref.botRoutingLayerRule)
				self.topRoutingLayerRule = LEFViaRuleLayer(swig_ref=swig_ref.topRoutingLayerRule)
				self.vias = []
		self.props = {}

	def __setitem__(self, key, value):
		self.props[key] = value

	def __getitem__(self, item):
		return self.props[item]

	def __contains__(self, item):
		if item in self.props:
			return True
		else:
			return False

	def export(self) -> LEFDEF.LEFViaRule:
		"""
		export the LEF via rule to LEFDEF C++ library

		:return: LEFViaRule in LEFDEF C++ library
		"""
		targ = LEFDEF.LEFViaRule()
		targ.name = self.name
		targ.isGenerate = self.isGenerate
		targ.isDefault = self.isDefault

		targ.cutLayerRule = self.cutLayerRule.export() if self.cutLayerRule is not None else LEFDEF.LEFViaRule()
		targ.botRoutingLayerRule = self.botRoutingLayerRule.export() if self.botRoutingLayerRule is not None else LEFDEF.LEFViaRule()
		targ.topRoutingLayerRule = self.topRoutingLayerRule.export() if self.topRoutingLayerRule is not None else LEFDEF.LEFViaRule()
		targ.via_names = LEFDEF.VecStr([via.name for via in self.vias])
		return targ

	def copy(self, lef: Union['LEF', 'LEFNonDefaultRule']) -> 'LEFViaRule':
		"""
		copy the object

		:param lef: LEF with LEF layers defined
		:return: copied object
		"""
		cp = LEFViaRule()
		cp.name = self.name
		cp.lef = lef
		cp.isGenerate = self.isGenerate
		cp.isDefault = self.isDefault

		cp.cutLayerRule = self.cutLayerRule.copy(lef) if self.cutLayerRule is not None else None
		cp.botRoutingLayerRule = self.botRoutingLayerRule.copy(lef) if self.botRoutingLayerRule is not None else None
		cp.topRoutingLayerRule = self.topRoutingLayerRule.copy(lef) if self.topRoutingLayerRule is not None else None
		cp.vias = [lef.vias[via.name] for via in self.vias]
		cp.props = self.props.copy()
		return cp

	def change_layer(self, layer_map: Dict[str, str], via_map: Dict[str, str], new_lef: Union['LEF', 'LEFNonDefaultRule']):
		"""
		change LEF layer based on layer_map. the resulting viarule will point layers in new_LEF

		:param layer_map: current layer name:new layer name map
		:param via_map: current via name:new via name map
		:param new_lef: LEF object which contains all the new layers and all the new vias
		"""
		self.cutLayerRule.change_layer(layer_map, new_lef)
		self.botRoutingLayerRule.change_layer(layer_map, new_lef)
		self.topRoutingLayerRule.change_layer(layer_map, new_lef)
		for via in self.vias:
			if via_map[via.name] in new_lef.vias:
				self.vias.append(new_lef.vias[via_map[via.name]])


class LEFSite:
	"""
	represents sites in LEF
	"""
	name: str
	'''
	name of the site
	'''
	lef: Union['LEF', None]
	'''
	lef which this layer is defined
	'''
	siteClass: int
	'''
	class of the site
	-1: NULL
	0: CORE
	1: PAD
	'''
	symmetry: int
	'''
	symmetry of the site (use OR for multiple selections)
	0: NULL
	1: X
	2: Y
	4: R90
	'''
	width: float
	'''
	width of the site
	'''
	height: float
	'''
	height of the site
	'''
	props: Dict[str, Any]
	'''
	user-defined properties
	'''

	def __init__(self, swig_ref: LEFDEF.LEFSite = None, lef: 'LEF' = None):
		"""
		create a LEF via

		:param swig_ref: imported LEF site from LEFDEF C++ library, if not specified, create empty object
		"""
		if swig_ref is None:
			self.name = ''
			self.lef = None
			self.siteClass = -1
			self.symmetry = 0
			self.width = -1
			self.height = -1
		else:
			self.name = swig_ref.name
			self.lef = lef
			self.siteClass = swig_ref.siteClass
			self.symmetry = swig_ref.symmetry
			self.width = swig_ref.width
			self.height = swig_ref.height
		self.props = {}

	def __setitem__(self, key, value):
		self.props[key] = value

	def __getitem__(self, item):
		return self.props[item]

	def __contains__(self, item):
		if item in self.props:
			return True
		else:
			return False

	def export(self) -> LEFDEF.LEFSite:
		"""
		export the LEF site to LEFDEF C++ library

		:return: LEFSite in LEFDEF C++ library
		"""
		targ = LEFDEF.LEFSite()
		targ.name = self.name
		targ.siteClass = self.siteClass
		targ.symmetry = self.symmetry
		targ.width = self.width if self.width is not None else -1
		targ.height = self.height if self.width is not None else -1
		return targ

	def copy(self, lef: 'LEF' = None) -> 'LEFSite':
		"""
		copy the object

		:return: copied object
		"""
		cp = LEFSite()
		cp.name = self.name
		cp.lef = lef
		cp.siteClass = self.siteClass
		cp.symmetry = self.symmetry
		cp.width = self.width
		cp.height = self.height
		cp.props = self.props.copy()
		return cp


class LEFMacroPin:
	"""
	represents pins in macros in LEF
	"""
	name: str
	'''
	name of the pin in its macro
	'''
	lef: Union['LEF', None]
	'''
	lef which this layer is defined
	'''
	type: int
	'''
	type of the pin in its macro
	-1: NULL
	0: analog
	1: clock
	2: ground
	3: power
	4: signal
	'''
	shape: int
	'''
	shape of the pin in its macro
	-1: NULL
	0: abutment
	1: ring
	2: feedthru
	'''
	direction: int
	'''
	direction of the pin in its macro
	-1: NULL
	0: input
	1: output
	2: output_tristate
	3: inout
	4: feedthru
	'''
	shapes: List['Shape']
	'''
	list of shapes of pin
	'''
	props: Dict[str, Any]
	'''
	user-defined properties
	'''

	def __init__(self, swig_ref: LEFDEF.LEFMacroPin = None, lef: Union['LEF', 'LEFNonDefaultRule'] = None):
		"""
		create a LEF macro pin

		:param swig_ref: imported LEF macro pin from LEFDEF C++ library, if not specified, create empty object
		:param lef: LEF with LEF layers defined
		"""
		if swig_ref is None:
			self.name = ''
			self.lef = None
			self.type = -1
			self.shape = -1
			self.direction = -1
			self.shapes = []
		else:
			self.name = swig_ref.name
			self.type = swig_ref.type
			self.shape = swig_ref.shape
			self.direction = swig_ref.direction
			if lef is not None:
				self.lef = lef
				self.shapes = [Shape(swig_ref=shape, layers=lef.layers) for shape in list(swig_ref.shapes)]
			else:
				self.lef = None
				self.shapes = [Shape(swig_ref=shape) for shape in list(swig_ref.shapes)]
		self.props = {}

	def __setitem__(self, key, value):
		self.props[key] = value

	def __getitem__(self, item):
		return self.props[item]

	def __contains__(self, item):
		if item in self.props:
			return True
		else:
			return False

	def export(self) -> LEFDEF.LEFMacroPin:
		"""
		export the LEF macro pin to LEFDEF C++ library

		:return: LEFMacroPin in LEFDEF C++ library
		"""
		targ = LEFDEF.LEFMacroPin()
		targ.name = self.name
		targ.type = self.type
		targ.shape = self.shape
		targ.direction = self.direction
		targ.shapes = LEFDEF.VecShape([shape.export() for shape in self.shapes])
		return targ

	def copy(self, lef: Union['LEF', 'LEFNonDefaultRule']) -> 'LEFMacroPin':
		"""
		copy the object

		:param lef: LEF with LEF layers defined
		:return: copied object
		"""
		cp = LEFMacroPin()
		cp.name = self.name
		cp.lef = lef
		cp.type = self.type
		cp.shape = self.shape
		cp.direction = self.direction
		cp.shapes = [shape.copy(lef.layers) for shape in self.shapes]
		cp.props = self.props.copy()
		return cp

	def change_layer(self, layer_map: Dict[str, str], new_lef: Union['LEF', 'LEFNonDefaultRule']):
		"""
		change LEF layer based on layer_map. the resulting macro pin will point layers in new_LEF

		:param layer_map: current layer name:new layer name map
		:param new_lef: LEF object which contains all the new layers
		"""
		for shape in self.shapes:
			shape.change_layers(layer_map, new_lef.layers)

	def scale(self, scale_factor: float):
		"""
		scale macro pin with a scale factor

		:param scale_factor: scale factor to scale macro
		:return: None
		"""
		for shape in self.shapes:
			shape.scale(scale_factor, snap_spacing=self.lef.manufacturingGrid)
		return


class LEFMacro:
	"""
	represents macro in LEF
	"""
	name: str
	'''
	name of the macro
	'''
	lef: Union['LEF', None]
	'''
	lef which this layer is defined
	'''
	macroClass: int
	'''
	class of the macro
	-1: NULL
	0: cover
	1: cover bump
	2: ring
	3: block
	4: block blackbox
	5: block soft
	6: pad
	7: pad input
	8: pad output
	9: pad inout
	10: pad power
	11: pad spacer
	12: pad areaio
	13: core
	14: core feedthru
	15: core tiehigh
	16: core tielow
	17: core spacer
	18: core antennacell
	19: core welltap
	20: endcap pre
	21: endcap post
	22: endcap topleft
	23: endcap topright
	24: endcap bottomleft
	25: endcap bottomright
	'''
	foreign: str
	'''
	foreign of the macro
	'''
	origin: 'Point'
	'''
	origin of the macro
	'''
	symmetry: int
	'''
	symmetry of the macro (use OR for multiple selections)
	0: NULL
	1: X
	2: Y
	4: R90
	'''
	site: Union['LEFSite', None]
	'''
	site of the macro
	'''
	width: float
	'''
	width of the macro
	'''
	height: float
	'''
	height of the macro
	'''
	pins: Dict[str, 'LEFMacroPin']
	'''
	pins of the macro
	'''
	OBSs: List['Shape']
	'''
	obstruction shapes in the macro
	'''
	props: Dict[str, Any]
	'''
	user-defined properties
	'''

	def __init__(self, swig_ref: LEFDEF.LEFMacro = None, lef: Union['LEF', 'LEFNonDefaultRule'] = None):
		"""
		create a LEF macro

		:param swig_ref: imported LEF macro from LEFDEF C++ library, if not specified, create empty object
		:param lef: LEF with LEF layers defined
		"""
		if swig_ref is None:
			self.name = ''
			self.lef = None
			self.macroClass = -1
			self.foreign = ''
			self.origin = Point(x=-1, y=-1, point_type=float)
			self.symmetry = 0
			self.site = None
			self.width = -1
			self.height = -1
			self.pins = {}
			self.OBSs = []
		else:
			self.name = swig_ref.name
			self.macroClass = swig_ref.macroClass
			self.foreign = swig_ref.foreign
			self.origin = Point(swig_ref=swig_ref.origin)
			self.symmetry = swig_ref.symmetry
			if lef is not None:
				self.lef = lef
				self.site = lef.sites[swig_ref.site_name] if swig_ref.site_name in lef.sites else None
			else:
				self.lef = None
				self.site = None
			self.width = swig_ref.width
			self.height = swig_ref.height
			if lef is not None:
				self.pins = {pin_name: LEFMacroPin(swig_ref=pin, lef=lef) for pin_name, pin in dict(swig_ref.pins).items()}
				self.OBSs = [Shape(swig_ref=obs, layers=lef.layers) for obs in list(swig_ref.OBSs)]
			else:
				self.pins = {pin_name: LEFMacroPin(swig_ref=pin) for pin_name, pin in dict(swig_ref.pins).items()}
				self.OBSs = [Shape(swig_ref=obs) for obs in list(swig_ref.OBSs)]
		self.props = {}

	def __setitem__(self, key, value):
		self.props[key] = value

	def __getitem__(self, item):
		return self.props[item]

	def __contains__(self, item):
		if item in self.props:
			return True
		else:
			return False

	def export(self) -> LEFDEF.LEFMacro:
		"""
		export the LEF macro to LEFDEF C++ library

		:return: LEFMacro in LEFDEF C++ library
		"""
		targ = LEFDEF.LEFMacro()
		targ.name = self.name
		targ.macroClass = self.macroClass
		targ.foreign = self.foreign
		targ.origin = self.origin.export()
		targ.symmetry = self.symmetry
		targ.site_name = self.site.name if self.site is not None else ''
		targ.width = self.width
		targ.height = self.height
		targ.pins = LEFDEF.MapStrLEFMacroPin({macroPin_name: macroPin_info.export() for macroPin_name, macroPin_info in self.pins.items()})
		targ.OBSs = LEFDEF.VecShape([shape.export() for shape in self.OBSs])
		return targ

	def copy(self, lef: Union['LEF', 'LEFNonDefaultRule']) -> 'LEFMacro':
		"""
		copy the object

		:param lef: LEF with LEF layers defined
		:return: copied object
		"""
		cp = LEFMacro()
		cp.name = self.name
		cp.lef = lef
		cp.macroClass = self.macroClass
		cp.foreign = self.foreign
		cp.origin = self.origin.copy()
		cp.symmetry = self.symmetry
		cp.site = lef.sites[self.site.name] if self.site is not None and self.site.name in lef.sites else None
		cp.width = self.width
		cp.height = self.height
		cp.pins = {macroPin_name: macroPin_info.copy(lef) for macroPin_name, macroPin_info in self.pins.items()}
		cp.OBSs = [shape.copy(lef.layers) for shape in self.OBSs]
		cp.props = self.props.copy()
		return cp

	def change_layer(self, layer_map: Dict[str, str], new_lef: Union['LEF', 'LEFNonDefaultRule']):
		"""
		change LEF layer based on layer_map. the resulting macro will point layers in new_lef

		:param layer_map: current layer name:new layer name map
		:param new_lef: LEF object which contains all the new layers
		"""
		for macroPin in self.pins.values():
			macroPin.change_layer(layer_map, new_lef)
		for shape in self.OBSs:
			shape.change_layers(layer_map, new_lef.layers)

	def scale(self, scale_factor: float, preserve_pins: bool = False):
		"""
		scale macro with a scale factor

		:param scale_factor: scale factor to scale macro
		:param preserve_pins: do NOT scale pin shapes (and OBS shapes) while scale macro size
		:return: None
		"""
		self.width = round(self.width * scale_factor / self.lef.manufacturingGrid) * self.lef.manufacturingGrid
		self.height = round(self.height * scale_factor / self.lef.manufacturingGrid) * self.lef.manufacturingGrid
		if not preserve_pins:
			for pin_name, pin_info in self.pins.items():
				pin_info.scale(scale_factor)
			for OBS in self.OBSs:
				OBS.scale(scale_factor, snap_spacing=self.lef.manufacturingGrid)
		return


class LEFMaxStackVia:
	"""
	represents max stack via of LEF
	"""
	maxStackVia: int
	'''
	maximum number of stacks of the via
	'''
	botRoutingLayer: Union['LEFLayer', None]
	'''
	bottom routing layer of the stacked via
	'''
	topRoutingLayer: Union['LEFLayer', None]
	'''
	top routing layer of the stacked via
	'''
	props: Dict[str, Any]
	'''
	user-defined properties
	'''

	def __init__(self, swig_ref: LEFDEF.LEFMaxStackVia = None, lef: Union['LEF', 'LEFNonDefaultRule'] = None):
		"""
		create a LEF max stack via

		:param swig_ref: imported LEF max stack via from LEFDEF C++ library, if not specified, create empty object
		:param lef: LEF with LEF layers defined
		"""
		if swig_ref is None:
			self.maxStackVia = -1
			self.botRoutingLayer = None
			self.topRoutingLayer = None
		else:
			self.maxStackVia = swig_ref.maxStackVia
			if lef is not None:
				self.botRoutingLayer = lef.layers[swig_ref.botRoutingLayer_name] if swig_ref.botRoutingLayer_name in lef.layers else None
				self.topRoutingLayer = lef.layers[swig_ref.topRoutingLayer_name] if swig_ref.topRoutingLayer_name in lef.layers else None
			else:
				self.botRoutingLayer = None
				self.topRoutingLayer = None
		self.props = {}

	def __setitem__(self, key, value):
		self.props[key] = value

	def __getitem__(self, item):
		return self.props[item]

	def __contains__(self, item):
		if item in self.props:
			return True
		else:
			return False

	def export(self) -> LEFDEF.LEFMaxStackVia:
		"""
		export the LEF max stack via to LEFDEF C++ library

		:return: LEFMaxStackVia in LEFDEF C++ library
		"""
		targ = LEFDEF.LEFMaxStackVia()
		targ.maxStackVia = self.maxStackVia
		targ.botRoutingLayer_name = self.botRoutingLayer.name if self.botRoutingLayer is not None else ''
		targ.topRoutingLayer_name = self.topRoutingLayer.name if self.topRoutingLayer is not None else ''
		return targ

	def copy(self, lef: Union['LEF', 'LEFNonDefaultRule']) -> 'LEFMaxStackVia':
		"""
		copy the object

		:param lef: LEF with LEF layers defined
		:return: copied object
		"""
		cp = LEFMaxStackVia()
		cp.maxStackVia = self.maxStackVia
		cp.botRoutingLayer = lef.layers[self.botRoutingLayer.name] if self.botRoutingLayer is not None and self.botRoutingLayer in lef.layers else None
		cp.topRoutingLayer = lef.layers[self.topRoutingLayer.name] if self.topRoutingLayer is not None and self.topRoutingLayer in lef.layers else None
		cp.props = self.props.copy()
		return cp

	def change_layer(self, layer_map: Dict[str, str], new_lef: Union['LEF', 'LEFNonDefaultRule']):
		"""
		change LEF layer based on layer_map. the resulting maxViaStack will point layers in new_LEF

		:param layer_map: current layer name:new layer name map
		:param new_lef: LEF object which contains all the new layers
		"""
		self.botRoutingLayer = new_lef.layers[layer_map[self.botRoutingLayer.name]] if self.botRoutingLayer is not None and self.botRoutingLayer.name in layer_map and layer_map[self.botRoutingLayer.name] in new_lef.layers else None
		self.topRoutingLayer = new_lef.layers[layer_map[self.topRoutingLayer.name]] if self.topRoutingLayer is not None and self.topRoutingLayer.name in layer_map and layer_map[self.topRoutingLayer.name] in new_lef.layers else None


class LEFNonDefaultRule:
	"""
	represent non-default rules (NDR) in LEF
	"""
	name: str
	'''
	name of the NDR
	'''
	cutLayers: List['LEFLayer']
	'''
	list of cut layers in the NDR
	'''
	routingLayers: List['LEFLayer']
	'''
	list of routing layers in the NDR
	'''
	layers: Dict[str, 'LEFLayer']
	'''
	list of all layers in the NDR
	'''
	vias: Dict[str, 'LEFVia']
	'''
	list of vias in the NDR
	'''
	props: Dict[str, Any]
	'''
	user-defined properties
	'''

	def __init__(self, swig_ref: LEFDEF.LEFNonDefaultRule = None):
		"""
		create a NDR

		:param swig_ref: imported LEF NDR from LEFDEF C++ library, if not specified, create empty object
		"""
		if swig_ref is None:
			self.name = ''
			self.cutLayers = []
			self.routingLayers = []
			self.layers = {}
			self.vias = {}
		else:
			# TODO: need to be fixed. LEFVia require LEF to instantiate
			self.name = swig_ref.name
			self.layers = {layer_name: LEFLayer(swig_ref=layer_info, lef=self) for layer_name, layer_info in dict(swig_ref.layers).items()}
			for layer_name in swig_ref.cutLayer_names:
				if layer_name in self.layers:
					self.cutLayers.append(self.layers[layer_name])
			for layer_name in swig_ref.routingLayer_names:
				if layer_name in self.layers:
					self.routingLayers.append(self.layers[layer_name])
			self.vias = {via_name: LEFVia(swig_ref=via_info, lef=self) for via_name, via_info in dict(swig_ref.vias).items()}
		self.props = {}

	def __setitem__(self, key, value):
		self.props[key] = value

	def __getitem__(self, item):
		return self.props[item]

	def __contains__(self, item):
		if item in self.props:
			return True
		else:
			return False

	def export(self) -> LEFDEF.LEFNonDefaultRule:
		"""
		export the NDR to LEFDEF C++ library

		:return: NDR in LEFDEF C++ library
		"""
		targ = LEFDEF.LEFNonDefaultRule()
		targ.name = self.name
		targ.layers = LEFDEF.MapStrLEFLayer({layer_name: layer_info.export() for layer_name, layer_info in self.layers.items()})
		targ.cutLayer_names = LEFDEF.VecStr([layer.name for layer in self.cutLayers])
		targ.routingLayer_names = LEFDEF.VecStr([layer.name for layer in self.routingLayers])
		targ.vias = LEFDEF.MapStrLEFVia({via_name: via_info.export() for via_name, via_info in self.vias.items()})
		return targ

	def copy(self) -> 'LEFNonDefaultRule':
		"""
		copy the object

		:return: copied object
		"""
		cp = LEFNonDefaultRule()
		cp.name = self.name
		cp.layers = {layer_name: layer_info.copy() for layer_name, layer_info in self.layers.items()}
		cp.cutLayer = [cp.layers[layer.name] for layer in self.cutLayers]
		cp.routingLayer = [cp.layers[layer.name] for layer in self.routingLayers]
		cp.vias = {via_name: via_info.copy(cp) for via_name, via_info in self.vias.items()}
		cp.props = self.props.copy()
		return cp


class LEFProp:
	"""
	represents LEF properties
	"""
	objType: int
	'''
	property object type
	-1: NULL
	0: library
	1: pin
	2: macro
	3: via
	4: viarule
	5: layer
	6: ndr
	'''
	name: str
	'''
	name of the property
	'''
	dataType: int
	'''
	data type of the property
	-1: NULL
	0: integer
	1: real
	2: string
	'''
	intRange: List[int]
	'''
	integer range
	'''
	doubleRange: List[float]
	'''
	floating-point range
	'''
	intValue: int
	'''
	integer value
	'''
	doubleValue: float
	'''
	floating-point value
	'''
	strValue: str
	'''
	string value
	'''
	props: Dict[str, Any]
	'''
	user-defined properties
	'''

	def __init__(self, swig_ref: LEFDEF.LEFProp = None):
		"""
		create a LEF property

		:param swig_ref: imported LEF property from LEFDEF C++ library, if not specified, create empty object
		"""
		if swig_ref is None:
			self.objType = -1
			self.name = ''
			self.dataType = -1
			self.intRange = []
			self.doubleRange = []
			self.intValue = 0
			self.doubleValue = 0
			self.strValue = ''
		else:
			self.objType = swig_ref.objType
			self.name = swig_ref.name
			self.dataType = swig_ref.dataType
			self.intRange = list(swig_ref.intRange)
			self.doubleRange = list(swig_ref.doubleRange)
			self.intValue = swig_ref.intValue
			self.doubleValue = swig_ref.doubleValue
			self.strValue = swig_ref.strValue
		self.props = {}

	def __setitem__(self, key, value):
		self.props[key] = value

	def __getitem__(self, item):
		return self.props[item]

	def __contains__(self, item):
		if item in self.props:
			return True
		else:
			return False

	def export(self) -> LEFDEF.LEFProp:
		"""
		export the LEF property to LEFDEF C++ library

		:return: LEFProp in LEFDEF C++ library
		"""
		targ = LEFDEF.LEFProp()
		targ.objType = self.objType
		targ.name = self.name
		targ.dataType = self.dataType
		targ.intRange = LEFDEF.VecInt(self.intRange)
		targ.doubleRange = LEFDEF.VecDouble(self.doubleRange)
		targ.intValue = self.intValue
		targ.doubleValue = self.doubleValue
		targ.strValue = self.strValue
		return targ

	def copy(self) -> 'LEFProp':
		"""
		copy the object

		:return: copied object
		"""
		cp = LEFProp()
		cp.objType = self.objType
		cp.name = self.name
		cp.dataType = self.dataType
		cp.intRange = self.intRange[:]
		cp.doubleRange = self.doubleRange[:]
		cp.intValue = self.intValue
		cp.doubleValue = self.doubleValue
		cp.strValue = self.strValue
		cp.props = self.props.copy()
		return cp


class LEF:
	"""
	represents LEF
	"""
	swigLEF: Union[LEFDEF.LEF, None]
	'''
	LEF object in LEFDEF C++ library
	'''
	lefVersion: str
	'''
	version of LEF
	'''
	busBitChars: str
	'''
	bus bit characters
	'''
	dividerChar: str
	'''
	hierarchy divider character
	'''
	dbUnits: int
	'''
	DB units
	'''
	manufacturingGrid: float
	'''
	manufacturing grid
	'''

	layers: Dict[str, 'LEFLayer']
	'''
	layers in LEF
	'''
	layer_order: List['LEFLayer']
	'''
	order of layers in LEF
	'''
	mastersliceLayers: List['LEFLayer']
	'''
	list of masterslice layers
	'''
	implantLayers: List['LEFLayer']
	'''
	list of implant layers
	'''
	routingLayers: List['LEFLayer']
	'''
	list of routing layers
	'''
	cutLayers: List['LEFLayer']
	'''
	list of cut layers
	'''
	overlapLayers: List['LEFLayer']
	'''
	list of overlap layers
	'''
	vias: Dict[str, 'LEFVia']
	'''
	vias defined in LEF
	'''
	viarules: Dict[str, 'LEFViaRule']
	'''
	via rules defined in LEF
	'''
	sites: Dict[str, 'LEFSite']
	'''
	sites defined in LEF
	'''
	macros: Dict[str, 'LEFMacro']
	'''
	macros defined in LEF
	'''

	clearanceMeasure: int
	'''
	clearance measure
	-1: NULL
	0: MAXXY
	1: EUCLIDEAN
	'''
	maxStackVia: List['LEFMaxStackVia']
	'''
	list of max via stack in LEF
	'''
	nonDefaultRule: Dict[str, 'LEFNonDefaultRule']
	'''
	NDR
	'''
	lefProps: List['LEFProp']
	'''
	list of LEF properties
	'''
	useMinSpacing: bool
	'''
	whether it uses min spacing or not
	'''
	props: Dict[str, Any]
	'''
	user-defined properties
	'''

	def __init__(self, lef_files: List[str] = None):
		"""
		create a LEF

		:param lef_files: LEF file to read to construct LEF
		"""
		self.swigLEF = None

		self.lefVersion = '5.8'
		self.busBitChars = '[]'
		self.dividerChar = '/'
		self.dbUnits = 100
		self.manufacturingGrid = 0.0

		self.layers = {}
		self.layer_order = []
		self.mastersliceLayers = []
		self.implantLayers = []
		self.routingLayers = []
		self.cutLayers = []
		self.overlapLayers = []
		self.vias = {}
		self.viarules = {}
		self.sites = {}
		self.macros = {}

		self.clearanceMeasure = 1
		self.maxStackVia = []
		self.nonDefaultRule = {}
		self.lefProps = []
		self.useMinSpacing = True
		if lef_files is not None:
			self.read_lef(lef_files)
		self.props = {}

	def __setitem__(self, key, value):
		self.props[key] = value

	def __getitem__(self, item):
		return self.props[item]

	def __contains__(self, item):
		if item in self.props:
			return True
		else:
			return False

	def read_lef(self, lef_files: List[str]):
		"""
		read LEF files

		:param lef_files: LEF files to read
		"""
		self.swigLEF = self.export()
		for lef_file in lef_files:
			if os.path.exists(lef_file):
				logger.info('run SWIG LEF to read %s' % lef_file)
				self.swigLEF.read_lef(lef_file)
			else:
				logger.error('input lef file %s does not exists. ignored.' % lef_file)
		self.import_swigLEF()
		logger.info('LEF for\n - %s \nis now ready' % ('\n - '.join(lef_files)))

	def import_swigLEF(self):
		"""
		convert LEF from LEFDEF C++ library to python LEF structure
		"""
		logger.info('convert SWIG LEF to python structure')
		self.lefVersion = self.swigLEF.lefVersion
		self.busBitChars = self.swigLEF.busBitChars
		self.dividerChar = self.swigLEF.dividerChar
		self.dbUnits = self.swigLEF.dbUnits
		self.manufacturingGrid = self.swigLEF.manufacturingGrid

		self.layers = {layer_name: LEFLayer(swig_ref=layer_info, lef=self) for layer_name, layer_info in dict(self.swigLEF.layers).items()}
		self.layer_order = [self.layers[layer_name] for layer_name in list(self.swigLEF.layer_order)]
		self.mastersliceLayers = [self.layers[layer_name] for layer_name in list(self.swigLEF.mastersliceLayer_names)]
		self.implantLayers = [self.layers[layer_name] for layer_name in list(self.swigLEF.implantLayer_names)]
		self.routingLayers = [self.layers[layer_name] for layer_name in list(self.swigLEF.routingLayer_names)]
		self.cutLayers = [self.layers[layer_name] for layer_name in list(self.swigLEF.cutLayer_names)]
		self.overlapLayers = [self.layers[layer_name] for layer_name in list(self.swigLEF.overlapLayer_names)]

		self.vias = {via_name: LEFVia(swig_ref=via_info, lef=self) for via_name, via_info in dict(self.swigLEF.vias).items()}
		self.viarules = {viarule_name: LEFViaRule(swig_ref=viarule_info, lef=self) for viarule_name, viarule_info in dict(self.swigLEF.viarules).items()}
		self.sites = {site_name: LEFSite(swig_ref=site_info, lef=self) for site_name, site_info in dict(self.swigLEF.sites).items()}
		self.macros = {macro_name: LEFMacro(swig_ref=macro_info, lef=self) for macro_name, macro_info in dict(self.swigLEF.macros).items()}

		self.clearanceMeasure = self.swigLEF.clearanceMeasure
		self.maxStackVia = [LEFMaxStackVia(swig_ref=msv, lef=self) for msv in list(self.swigLEF.maxViaStack)]
		self.nonDefaultRule = {ndr_name: LEFNonDefaultRule(swig_ref=ndr_info) for ndr_name, ndr_info in dict(self.swigLEF.nonDefaultRule).items()}
		self.lefProps = [LEFProp(swig_ref=prop) for prop in list(self.swigLEF.props)]
		self.useMinSpacing = self.swigLEF.useMinSpacing

	def export(self) -> LEFDEF.LEF:
		"""
		export the LEF to LEFDEF C++ library

		:return: LEF in LEFDEF C++ library
		"""
		logger.info('convert LEF to C structure for SWIG LEF')
		targ = LEFDEF.LEF()
		targ.lefVersion = self.lefVersion
		targ.busBitChars = self.busBitChars
		targ.dividerChar = self.dividerChar
		targ.dbUnits = self.dbUnits
		targ.manufacturingGrid = self.manufacturingGrid if self.manufacturingGrid is not None else -1

		targ.layers = LEFDEF.MapStrLEFLayer({layer_name: layer_info.export() for layer_name, layer_info in self.layers.items()})
		targ.layer_order = LEFDEF.VecStr([layer.name for layer in self.layer_order])
		targ.mastersliceLayer_names = LEFDEF.VecStr([layer.name for layer in self.mastersliceLayers])
		targ.implantLayer_names = LEFDEF.VecStr([layer.name for layer in self.implantLayers])
		targ.routingLayer_names = LEFDEF.VecStr([layer.name for layer in self.routingLayers])
		targ.cutLayer_names = LEFDEF.VecStr([layer.name for layer in self.cutLayers])
		targ.overlapLayer_names = LEFDEF.VecStr([layer.name for layer in self.overlapLayers])

		targ.vias = LEFDEF.MapStrLEFVia({via_name: via_info.export() for via_name, via_info in self.vias.items()})
		targ.viarules = LEFDEF.MapStrLEFViaRule({viarule_name: viarule_info.export() for viarule_name, viarule_info in self.viarules.items()})
		targ.sites = LEFDEF.MapStrLEFSite({site_name: site_info.export() for site_name, site_info in self.sites.items()})
		targ.macros = LEFDEF.MapStrLEFMacro({macro_name: macro_info.export() for macro_name, macro_info in self.macros.items()})

		targ.clearanceMeasure = self.clearanceMeasure
		targ.maxViaStack = LEFDEF.VecLEFMaxStackVia([msv.export() for msv in self.maxStackVia])
		targ.nonDefaultRule = LEFDEF.MapStrLEFNDR({ndr_name: ndr_info.export() for ndr_name, ndr_info in self.nonDefaultRule.items()})
		targ.props = LEFDEF.VecLEFProp([prop.export() for prop in self.lefProps])
		targ.useMinSpacing = self.useMinSpacing
		return targ

	def copy(self) -> 'LEF':
		"""
		copy the object

		:return: copied object
		"""
		cp = LEF()
		cp.lefVersion = self.lefVersion
		cp.busBitChars = self.busBitChars
		cp.dividerChar = self.dividerChar
		cp.dbUnits = self.dbUnits
		cp.manufacturingGrid = self.manufacturingGrid

		cp.layers = {layer_name: layer_info.copy(lef=cp) for layer_name, layer_info in self.layers.items()}
		cp.layer_order = [cp.layers[layer.name] for layer in self.layer_order]
		cp.mastersliceLayers = [cp.layers[layer.name] for layer in self.mastersliceLayers]
		cp.implantLayers = [cp.layers[layer.name] for layer in self.implantLayers]
		cp.routingLayers = [cp.layers[layer.name] for layer in self.mastersliceLayers]
		cp.cutLayers = [cp.layers[layer.name] for layer in self.cutLayers]
		cp.overlapLayers = [cp.layers[layer.name] for layer in self.overlapLayers]

		cp.vias = {via_name: via_info.copy(cp) for via_name, via_info in self.vias.items()}
		cp.viarules = {viarule_name: viarule_info.copy(cp) for viarule_name, viarule_info in self.viarules.items()}
		cp.sites = {site_name: site_info.copy(cp) for site_name, site_info in self.sites.items()}
		cp.macros = {macro_name: macro_info.copy(cp) for macro_name, macro_info in self.macros.items()}

		cp.clearanceMeasure = self.clearanceMeasure
		cp.maxStackVia = [msv.copy(cp) for msv in self.maxStackVia]
		cp.nonDefaultRule = {ndr_name: ndr_info.copy() for ndr_name, ndr_info in self.nonDefaultRule.items()}
		cp.lefProps = [prop.copy() for prop in self.lefProps]
		cp.useMinSpacing = self.useMinSpacing
		cp.props = self.props.copy()
		return cp

	def copy_only_header(self) -> 'LEF':
		"""
		copy only header of LEF (layers, vias, viarules, sites, macros, maxStackVia, NDR will be excluded for copying)

		:return: copied object
		"""
		cp = LEF()
		cp.lefVersion = self.lefVersion
		cp.busBitChars = self.busBitChars
		cp.dividerChar = self.dividerChar
		cp.dbUnits = self.dbUnits
		cp.manufacturingGrid = self.manufacturingGrid

		cp.clearanceMeasure = self.clearanceMeasure
		cp.lefProps = [prop.copy() for prop in self.lefProps]
		cp.useMinSpacing = self.useMinSpacing
		cp.props = self.props.copy()
		return cp

	def get_type_layers(self, layer_type: int) -> List['LEFLayer']:
		"""
		get mastersliceLayers, implantLayers, routingLayers, cutLayers, overlapLayers depending on type

		:param layer_type: layer type
		:return: corresponding layer list
		"""
		if layer_type == 0:
			return self.mastersliceLayers
		elif layer_type == 1:
			return self.implantLayers
		elif layer_type == 2:
			return self.routingLayers
		elif layer_type == 3:
			return self.cutLayers
		elif layer_type == 4:
			return self.overlapLayers
		else:
			return []

	def write_lef(self, lef_file: str, only_macro: bool = False) -> LEFDEF.LEF:
		"""
		write this LEF into a LEF file

		:param lef_file: LEF file to write
		:return: LEF in LEFDEF C++ library
		"""
		logger.info('start writing LEF file %s' % lef_file)
		self.swigLEF = self.export()
		logger.info('run SWIG LEF to write %s' % lef_file)
		self.swigLEF.write_lef(lef_file, only_macro)
		logger.info('writing %s done' % lef_file)
		return self.swigLEF

	def make_3d_lef(self, impl_type: str, num_layers: List[int], ilv_size: List[float], ilv_spacing: List[float], row_splitting: bool = False) -> Tuple['LEF', List[str], Dict[str, List[Dict[str, str]]]]:
		"""
		make a 3D LEF for 3D ICs (this is used in in pnr 3d_route stage)

		:param impl_type: type of the 3D IC (supported type: 'f2b', 'f2f')
		:param num_layers: number of routing layers used in each partitions (tiers)
		:param ilv_size: sizes of inter-layer via (if there are three tiers, there should be two elements in this list. first one is for ilv btw tier0 and tier1, and the second one is for btw tier1 and tier2)
		:param ilv_spacing: spacings of inter-layer via (if there are three tiers, there should be two elements in this list. first one is for ilv btw tier0 and tier1, and the second one is for btw tier1 and tier2)
		:param row_splitting: make macro, site half height (used in compact2D)
		:return: 3D LEF, list of ILV cut layer names, 2d to 3d mapping information for layer, via, viarule, site, macro
		"""
		logger.info('start generating 3D LEF')
		logger.info('- implementation type: %s' % impl_type)
		logger.info('- number of layers: %s' % str(num_layers))
		logger.info('- ILV size: %s' % str(ilv_size))
		logger.info('- ILV spacing: %s' % str(ilv_spacing))
		logger.info('- enable row splitting: %s' % str(row_splitting))
		num_tiers = len(num_layers)
		logger.info('-- number of tiers: %d' % num_tiers)

		lef_3d = self.copy_only_header()
		ilv_layer_names = []
		maps_2d_to_3d = {}
		maps_2d_to_3d['layer'] = [{} for i in range(num_tiers)]
		maps_2d_to_3d['via'] = [{} for i in range(num_tiers)]
		maps_2d_to_3d['viarule'] = [{} for i in range(num_tiers)]
		maps_2d_to_3d['site'] = [{} for i in range(num_tiers)]
		maps_2d_to_3d['macro'] = [{} for i in range(num_tiers)]
		if impl_type != 'f2b' and impl_type != 'f2f':
			logger.error('invalid implementation type %s. producing empty 3D LEF and 2D to 3D mapping information' % impl_type)
			return lef_3d, ilv_layer_names, maps_2d_to_3d

		botRoutingLayer_idx = self.layer_order.index(self.routingLayers[0])
		topRoutingLayer_idx = self.layer_order.index(self.routingLayers[len(self.routingLayers) - 1])

		logger.info('building 3D LEF layers')
		# header layers (before routing layers and cut layers)
		header_layers = self.layer_order[0:botRoutingLayer_idx]
		for layer_info in header_layers:
			lef_3d.layers[layer_info.name] = layer_info.copy(self)
			lef_3d.layer_order.append(lef_3d.layers[layer_info.name])
			lef_3d.get_type_layers(layer_info.type).append(lef_3d.layers[layer_info.name])
			for tier_layer_map in maps_2d_to_3d['layer']:
				tier_layer_map[layer_info.name] = layer_info.name

		# routing layers and cut layers
		bot_to_top = True
		for tier_num in range(num_tiers):
			tier_num_layers = num_layers[tier_num]
			tier_topRoutingLayer_idx = self.layer_order.index(self.routingLayers[tier_num_layers - 1])
			tier_routing_layers = self.layer_order[botRoutingLayer_idx:tier_topRoutingLayer_idx + 1]
			if not bot_to_top:
				tier_routing_layers = reversed(tier_routing_layers)

			for tier_routing_layer in tier_routing_layers:
				tier_layer_name = tier_routing_layer.name + '_T' + str(tier_num)
				lef_3d.layers[tier_layer_name] = tier_routing_layer.copy(self)
				lef_3d.layers[tier_layer_name].name = tier_layer_name
				lef_3d.layer_order.append(lef_3d.layers[tier_layer_name])
				lef_3d.get_type_layers(tier_routing_layer.type).append(lef_3d.layers[tier_layer_name])
				maps_2d_to_3d['layer'][tier_num][tier_routing_layer.name] = tier_layer_name

			if tier_num != num_tiers - 1:
				ilv_layer = LEFLayer()
				ilv_layer.name = 'ILV_T' + str(tier_num) + str(tier_num + 1)
				ilv_layer.id = len(lef_3d.layers)
				ilv_layer.type = 3
				ilv_layer.width = ilv_size[tier_num]
				ilv_layer.spacing = ilv_spacing[tier_num]
				lef_3d.layers[ilv_layer.name] = ilv_layer
				lef_3d.layer_order.append(lef_3d.layers[ilv_layer.name])
				lef_3d.cutLayers.append(lef_3d.layers[ilv_layer.name])
				ilv_layer_names.append(ilv_layer.name)

			if impl_type == 'f2f':
				bot_to_top = not bot_to_top

		# footer layers (after routing layers and cut layers)
		footer_layers = self.layer_order[topRoutingLayer_idx + 1:]
		for layer_info in footer_layers:
			lef_3d.layers[layer_info.name] = layer_info.copy(self)
			lef_3d.layer_order.append(lef_3d.layers[layer_info.name])
			lef_3d.get_type_layers(layer_info.type).append(lef_3d.layers[layer_info.name])
			for tier_layer_map in maps_2d_to_3d['layer']:
				tier_layer_map[layer_info.name] = layer_info.name

		logger.info('building 3D LEF vias')
		for via_name, via_info in self.vias.items():
			for tier_num in range(num_tiers):
				if self.routingLayers.index(via_info.topRoutingLayer) < num_layers[tier_num]:
					via_3d_name = via_name + '_T' + str(tier_num)
					lef_3d.vias[via_3d_name] = via_info.copy(self)
					lef_3d.vias[via_3d_name].name = via_3d_name
					lef_3d.vias[via_3d_name].change_layer(maps_2d_to_3d['layer'][tier_num], lef_3d)
					maps_2d_to_3d['via'][tier_num][via_name] = via_3d_name

		# insert ILV vias
		cutLayer_idx = -1
		for tier_num in range(num_tiers - 1):
			cutLayer_idx += num_layers[tier_num]
			ilv = LEFVia()
			ilv.name = 'VIA_' + lef_3d.cutLayers[cutLayer_idx].name
			ilv.isDefault = True

			ilv.cutLayer = lef_3d.cutLayers[cutLayer_idx]
			cut_shape = Shape(shape_type=1)
			cut_shape.layer = ilv.cutLayer
			cut_shape.rect = Rect(llx=-1 * (ilv_size[tier_num] / 2),
								  lly=-1 * (ilv_size[tier_num] / 2),
								  urx=ilv_size[tier_num] / 2,
								  ury=ilv_size[tier_num] / 2,
								  rect_type=float)
			ilv.cutShapes.append(cut_shape)

			ilv.botRoutingLayer = lef_3d.routingLayers[cutLayer_idx]
			botRouting_shape = Shape(shape_type=1)
			botRouting_shape.layer = ilv.botRoutingLayer
			enclosure_size = ilv.botRoutingLayer.width if ilv.botRoutingLayer.width is not None and ilv.botRoutingLayer.width != -1 else ilv.botRoutingLayer.min_width
			botRouting_shape.rect = Rect(llx=-1 * (enclosure_size / 2),
										 lly=-1 * (enclosure_size / 2),
										 urx=enclosure_size / 2,
										 ury=enclosure_size / 2,
										 rect_type=float)
			ilv.botRoutingShapes.append(botRouting_shape)

			ilv.topRoutingLayer = lef_3d.routingLayers[cutLayer_idx + 1]
			topRouting_shape = Shape(shape_type=1)
			topRouting_shape.layer = ilv.topRoutingLayer
			enclosure_size = ilv.topRoutingLayer.width if ilv.topRoutingLayer.width is not None and ilv.topRoutingLayer.width != -1 else ilv.topRoutingLayer.min_width
			topRouting_shape.rect = Rect(llx=-1 * (enclosure_size / 2),
										 lly=-1 * (enclosure_size / 2),
										 urx=enclosure_size / 2,
										 ury=enclosure_size / 2,
										 rect_type=float)
			ilv.topRoutingShapes.append(topRouting_shape)

			lef_3d.vias[ilv.name] = ilv

		logger.info('building 3D LEF via rules')
		for viarule_name, viarule_info in self.viarules.items():
			for tier_num in range(num_tiers):
				if self.routingLayers.index(viarule_info.topRoutingLayerRule.layer) < num_layers[tier_num]:
					viarule_3d_name = viarule_name + '_T' + str(tier_num)
					lef_3d.viarules[viarule_3d_name] = viarule_info.copy(self)
					lef_3d.viarules[viarule_3d_name].name = viarule_3d_name
					lef_3d.viarules[viarule_3d_name].change_layer(maps_2d_to_3d['layer'][tier_num], maps_2d_to_3d['via'][tier_num], lef_3d)
					maps_2d_to_3d['viarule'][tier_num][viarule_name] = viarule_3d_name

		# insert ILV via rules
		cutLayer_idx = -1
		for tier_num in range(num_tiers - 1):
			cutLayer_idx += num_layers[tier_num]
			ilv_rule = LEFViaRule()
			ilv_rule.name = 'VIARULE_' + lef_3d.cutLayers[cutLayer_idx].name
			ilv_rule.isGenerate = True

			ilv_rule.cutLayerRule = LEFViaRuleLayer()
			ilv_rule.cutLayerRule.layer = lef_3d.cutLayers[cutLayer_idx]
			cut_shape = Shape(shape_type=1)
			cut_shape.layer = lef_3d.cutLayers[cutLayer_idx]
			cut_shape.rect = Rect(llx=-1 * (ilv_size[tier_num] / 2),
								  lly=-1 * (ilv_size[tier_num] / 2),
								  urx=ilv_size[tier_num] / 2,
								  ury=ilv_size[tier_num] / 2,
								  rect_type=float)
			ilv_rule.cutLayerRule.shapes.append(cut_shape)
			ilv_rule.cutLayerRule.spacing = [ilv_spacing[tier_num]] * 2

			ilv_rule.botRoutingLayerRule = LEFViaRuleLayer()
			ilv_rule.botRoutingLayerRule.layer = lef_3d.routingLayers[cutLayer_idx]
			enclosure_size = ilv_rule.botRoutingLayerRule.layer.width if ilv_rule.botRoutingLayerRule.layer.width is not None and ilv_rule.botRoutingLayerRule.layer.width != -1 else ilv_rule.botRoutingLayerRule.layer.min_width
			ilv_rule.botRoutingLayerRule.enclosure = [enclosure_size] * 2

			ilv_rule.topRoutingLayerRule = LEFViaRuleLayer()
			ilv_rule.topRoutingLayerRule.layer = lef_3d.routingLayers[cutLayer_idx + 1]
			enclosure_size = ilv_rule.topRoutingLayerRule.layer.width if ilv_rule.topRoutingLayerRule.layer.width is not None and ilv_rule.topRoutingLayerRule.layer.width != -1 else ilv_rule.topRoutingLayerRule.layer.min_width
			ilv_rule.topRoutingLayerRule.enclosure = [enclosure_size] * 2

			lef_3d.viarules[ilv_rule.name] = ilv_rule

		logger.info('building 3D LEF sites')
		if row_splitting:
			for site_name, site_info in self.sites.items():
				for tier_num in range(num_tiers):
					site_3d_name = site_name + '_T' + str(tier_num)
					lef_3d.sites[site_3d_name] = site_info.copy()
					lef_3d.sites[site_3d_name].name = site_3d_name
					lef_3d.sites[site_3d_name].height /= 2
					maps_2d_to_3d['site'][tier_num][site_name] = site_3d_name
		else:
			lef_3d.sites = {site_name: site_info.copy() for site_name, site_info in self.sites.items()}
		from flow_var_utils import flow_vars as FLOW_VARS
		logger.info('building 3D LEF macros')
		for macro_name, macro_info in self.macros.items():
			for tier_num in range(num_tiers):
				macro_3d_name = macro_name + '_T' + str(tier_num)
				lef_3d.macros[macro_3d_name] = macro_info.copy(self)
				lef_3d.macros[macro_3d_name].name = macro_3d_name
				lef_3d.macros[macro_3d_name].foreign = lef_3d.macros[macro_3d_name].foreign + '_T' + str(tier_num)
				lef_3d.macros[macro_3d_name].change_layer(maps_2d_to_3d['layer'][tier_num], lef_3d)
				if pdflow.has_memory() and macro_name in FLOW_VARS['MEMORY_CELLS']:
					if row_splitting:
						lef_3d.macros[macro_3d_name].height /= 2
				else:
					if row_splitting:
						lef_3d.macros[macro_3d_name].height /= 2
						if tier_num % 2 == 1:
							lef_3d.macros[macro_3d_name].origin.y = -1 * lef_3d.macros[macro_3d_name].height
						lef_3d.macros[macro_3d_name].site = lef_3d.sites[maps_2d_to_3d['site'][tier_num][lef_3d.macros[macro_3d_name].site.name]]
					else:
						lef_3d.macros[macro_3d_name].site = lef_3d.sites[lef_3d.macros[macro_3d_name].site.name]
				maps_2d_to_3d['macro'][tier_num][macro_name] = macro_3d_name

		logger.info('building 3D LEF max stack via')
		for msv in self.maxStackVia:
			for tier_num in range(num_tiers):
				msv_3d = msv.copy(self)
				if self.layer_order.index(msv_3d.topRoutingLayer) > num_layers[tier_num] - 1:
					msv_3d.topRoutingLayer = self.routingLayers[num_layers[tier_num] - 1]
				msv_3d.change_layer(maps_2d_to_3d['layer'][tier_num], lef_3d)
				lef_3d.maxStackVia.append(msv_3d)

		# TODO: need to deal with nonDefaultRule

		logger.info('end generating 3D LEF')
		return lef_3d, ilv_layer_names, maps_2d_to_3d

	def delete_layer(self, layer_name: str, keep_related: bool = False):
		"""
		delete a layer from this LEF

		:param layer_name: the name of layer to delete
		:param keep_related: if True, it will not delete any vias, viarules, sites, macros etc, which is using the layer to be delete. if False, it will delete the related vias, viarules, sites, macros, etc.
		"""
		if layer_name in self.layers:
			if not keep_related:
				obj_to_delete = []
				for via_name in list(self.vias.keys()):
					via_info = self.vias[via_name]
					if via_info.topRoutingLayer.name == layer_name or via_info.botRoutingLayer.name == layer_name or via_info.cutLayer.name == layer_name:
						logger.warning('delete via %s which is related to layer %s' % (via_name, layer_name))
						del self.vias[via_name]

				for viarule_name in list(self.viarules.keys()):
					viarule_info = self.viarules[viarule_name]
					if viarule_info.topRoutingLayerRule.layer.name == layer_name or viarule_info.botRoutingLayerRule.layer.name == layer_name or viarule_info.cutLayerRule.layer.name == layer_name:
						logger.warning('delete via rule %s which is related to layer %s' % (viarule_name, layer_name))
						del self.viarules[viarule_name]

				for macro_name in list(self.macros.keys()):
					macro_info = self.macros[macro_name]
					for pin_name, pin_info in macro_info.pins.items():
						for shape in pin_info.shapes:
							if shape.layer.name == layer_name:
								logger.warn('delete macro %s which is related to layer %s' % (macro_name, layer_name))
								del self.macros[macro_name]
								continue
						for obs in macro_info.OBSs:
							if obs.layer.name == layer_name:
								logger.warn('delete macro %s which is related to layer %s' % (macro_name, layer_name))
								del self.macros[macro_name]
								continue

				for msv in self.maxStackVia:
					if msv.botRoutingLayer.name == layer_name:
						# as the next routing layer order is current routing layer + 2 (consider cut layer between them)
						msv.botRoutingLayer = self.layer_order[self.layer_order.index(self.layers[layer_name]) + 2]
						logger.warning('changing bottom routing layer for max stack via from %s to %s' % (layer_name, msv.botRoutingLayer.name))
					if msv.topRoutingLayer.name == layer_name:
						# as the previous routing layer order is current routing layer - 2 (consider cut layer between them)
						msv.topRoutingLayer = self.layer_order[self.layer_order.index(self.layers[layer_name]) - 2]
						logger.warning('changing top routing layer for max stack via from %s to %s' % (layer_name, msv.topRoutingLayer.name))

			self.get_type_layers(self.layers[layer_name].type).remove(self.layers[layer_name])
			self.layer_order.remove(self.layers[layer_name])
			del self.layers[layer_name]
		else:
			logger.error('layer %s does not exist' % layer_name)

	def duplicate_layer(self, ref_layer_name: str, targ_layer_name: str, after_layer_name: str = None):
		"""
		duplicate a layer in this LEF

		:param ref_layer_name: the name of the existing layer to be duplicated
		:param targ_layer_name: the name of the duplicated layer
		:param after_layer_name: put after after_layer_name. if None, it will be placed at the last
		"""
		if ref_layer_name in self.layers:
			if targ_layer_name not in self.layers:
				self.layers[targ_layer_name] = self.layers[ref_layer_name].copy()
				if after_layer_name is not None and after_layer_name in self.layers:
					after_layer_idx = self.layer_order.index(self.layers[after_layer_name])
					self.layer_order.insert(after_layer_idx+1, self.layers[targ_layer_name])
					layer_idx = -1
					for layer in reversed(self.layers[0:after_layer_idx].values()):
						if layer.type == self.layers[targ_layer_name].type:
							layer_idx = self.get_type_layers(layer.type).index(layer)
							break
					self.get_type_layers(self.layers[targ_layer_name].type).insert(layer_idx+1, self.layers[targ_layer_name])
				else:
					if after_layer_name is not None and after_layer_name not in self.layers:
						logger.warning('after layer name %s does not exist. put duplicated layer to the last')
					self.layer_order.append(self.layers[targ_layer_name])
					self.get_type_layers(self.layers[targ_layer_name].type).append(self.layers[targ_layer_name])
			else:
				logger.error('target layer name %s is already being used' % (targ_layer_name))
		else:
			logger.error('layer %s does not exist' % (targ_layer_name))

	def rename_layer(self, layer_name: str, new_layer_name: str):
		"""
		rename a layer in this LEF

		:param layer_name: the name of the existing layer
		:param new_layer_name: the new name of the layer
		"""
		if layer_name in self.layers:
			if new_layer_name not in self.layers:
				self.layers[layer_name].name = new_layer_name
				self.layers[new_layer_name] = self.layers.pop(layer_name)
			else:
				logger.error('new layer name %s is already being used' % (new_layer_name))
		else:
			logger.error('target layer %s does not exist' % (layer_name))

	def scale_macro(self, scale_factor: float, preserve_pins: bool = False):
		"""
		scale macros defined in this LEF with a scale factor

		:param scale_factor: scale factor to scale macro
		:param preserve_pins: do NOT scale pin shapes (and OBS shapes) while scale macro size
		:return: None
		"""
		for macro_name, macro_info in self.macros.items():
			macro_info.scale(scale_factor, preserve_pins)
		return


#########################################
# From DEF.hpp
#########################################
class DEFBlkg:
	"""
	represents a blockage in designs
	"""
	type: int
	'''
	type of blockage
	-1: NULL
	0: placement blockage
	1: routing blockage
	'''
	layer: Union['LEFLayer', None]
	'''
	for routing blockage, LEF layer which the routing blockage lies on
	'''
	partial: float
	'''
	for placement blockage, initial placement should not use more than 'partial' percentage of the blockage area for standard cells (between 0.0 and 100.0) (std cell area in blockage area/blockage area*100 <= this value)
	'''
	shapes: List['Shape']
	'''
	list of shapes of the blockage
	'''
	component: Union['DEFComponent', None]
	'''
	components which is associated with this blockage
	'''
	props: Dict[str, Any]
	'''
	user-defined properties
	'''

	def __init__(self, swig_ref: LEFDEF.DEFBlkg = None, design: 'DEFDesign' = None):
		"""
		create a blockage in the specified design

		:param swig_ref: imported DEFBlkg from LEFDEF C++ library, if not specified, create empty object
		:param design: DEFDesign which this DEFBlkg belongs to. DEFDesign should have a valid DEF as member, and the DEF should have a valid LEF as member which has full list of LEF layers
		"""
		if swig_ref is None:
			self.type = -1
			self.layer = None
			self.partial = -1.0
			self.shapes = []
			self.component = None
		else:
			self.type = swig_ref.type
			if design is not None:
				self.layer = design.DEF.LEF.layers[swig_ref.layer_name] if swig_ref.layer_name in design.DEF.LEF.layers else None
			else:
				self.layer = None
			self.partial = swig_ref.partial
			self.shapes = [Shape(shape, design.DEF.LEF.layers) for shape in list(swig_ref.shapes)]
			if design is not None:
				self.component = design.components[swig_ref.component_name] if swig_ref.component_name in design.components else None
			else:
				self.component = None
		self.props = {}

	def __setitem__(self, key, value):
		self.props[key] = value

	def __getitem__(self, item):
		return self.props[item]

	def __contains__(self, item):
		if item in self.props:
			return True
		else:
			return False

	def export(self) -> LEFDEF.DEFBlkg:
		"""
		export the blockage to LEFDEF C++ library

		:return: DEFBlkg in LEFDEF C++ library
		"""
		targ = LEFDEF.DEFBlkg()
		targ.type = self.type
		targ.layer_name = self.layer.name if self.layer is not None else ''
		targ.partial = self.partial
		targ.shapes = LEFDEF.VecShape([shape.export() for shape in self.shapes])
		targ.component_name = self.component.name if self.component is not None else ''
		return targ

	def copy(self, design: 'DEFDesign') -> 'DEFBlkg':
		"""
		copy the object

		:param design: DEFDesign which this DEFBlkg belongs to. DEFDesign should have a valid DEF as member, and the DEF should have a valid LEF as member which has full list of LEF layers
		:return: copied object
		"""
		cp = DEFBlkg()
		cp.type = self.type
		cp.layer = design.DEF.LEF.layers[self.layer.name] if self.layer is not None and self.layer.name in design.DEF.LEF.layers else None
		cp.partial = self.partial
		cp.shapes = [shape.copy(design.DEF.LEF.layers) for shape in self.shapes]
		cp.component = design.components[self.component.name] if self.component is not None else None
		cp.props = self.props.copy()
		return cp

	def change_layer(self, layer_map: Dict[str, str], new_lef: Union['LEF', 'LEFNonDefaultRule']):
		"""
		change LEF layer based on layer_map. the resulting blockage will point layers in new_lef

		:param layer_map: current layer name:new layer name map
		:param new_lef: LEF object which contains all the new layers
		"""
		self.layer = new_lef.layers[layer_map[self.layer.name]] if self.layer is not None and self.layer.name in layer_map and layer_map[self.layer.name] in new_lef.layers else None


class DEFProp:
	"""
	represents DEF properties
	"""
	objType: int
	'''
	property object type
	-1: NULL
	0: component
	1: componentpin
	2: design
	3: group
	4: net
	5: nondefaultrule
	6: region
	7: row
	8: specialnet
	'''
	name: str
	'''
	name of the property
	'''
	dataType: int
	'''
	data type of the property
	-1: NULL
	0: integer
	1: real
	2: string
	'''
	intRange: List[int]
	'''
	integer range
	'''
	doubleRange: List[float]
	'''
	floating-point range
	'''
	intValue: int
	'''
	integer value
	'''
	doubleValue: float
	'''
	floating-point value
	'''
	strValue: str
	'''
	string value
	'''
	props: Dict[str, Any]
	'''
	user-defined properties
	'''

	def __init__(self, swig_ref: LEFDEF.DEFProp = None):
		"""
		create a DEF property

		:param swig_ref: imported DEF property from LEFDEF C++ library, if not specified, create empty object
		"""
		if swig_ref is None:
			self.objType = -1
			self.name = ''
			self.dataType = -1
			self.intRange = []
			self.doubleRange = []
			self.intValue = 0
			self.doubleValue = 0
			self.strValue = ''
		else:
			self.objType = swig_ref.objType
			self.name = swig_ref.name
			self.dataType = swig_ref.dataType
			self.intRange = list(swig_ref.intRange)
			self.doubleRange = list(swig_ref.doubleRange)
			self.intValue = swig_ref.intValue
			self.doubleValue = swig_ref.doubleValue
			self.strValue = swig_ref.strValue
		self.props = {}

	def __setitem__(self, key, value):
		self.props[key] = value

	def __getitem__(self, item):
		return self.props[item]

	def __contains__(self, item):
		if item in self.props:
			return True
		else:
			return False

	def export(self) -> LEFDEF.DEFProp:
		"""
		export the DEF property to LEFDEF C++ library

		:return: DEFProp in LEFDEF C++ library
		"""
		targ = LEFDEF.DEFProp()
		targ.objType = self.objType
		targ.name = self.name
		targ.dataType = self.dataType
		targ.intRange = LEFDEF.VecInt(self.intRange)
		targ.doubleRange = LEFDEF.VecDouble(self.doubleRange)
		targ.intValue = self.intValue
		targ.doubleValue = self.doubleValue
		targ.strValue = self.strValue
		return targ

	def copy(self) -> 'DEFProp':
		"""
		copy the object

		:return: copied object
		"""
		cp = DEFProp()
		cp.objType = self.objType
		cp.name = self.name
		cp.dataType = self.dataType
		cp.intRange = self.intRange[:]
		cp.doubleRange = self.doubleRange[:]
		cp.intValue = self.intValue
		cp.doubleValue = self.doubleValue
		cp.strValue = self.strValue
		cp.props = self.props.copy()
		return cp


class DEFRow:
	"""
	represents rows in a design
	"""
	name: str
	'''
	name of the row
	'''
	design: Union['DEFDesign', None]
	'''
	design which this row belongs to
	'''
	site: Union['LEFSite', None]
	'''
	LEF site associated with this row
	'''
	origin: 'Point'
	'''
	origin of the row
	'''
	orientation: int
	'''
	orientation of the row
	-1: NULL
	0: N
	1: S
	2: W
	3: E
	4: FN
	5: FS
	6: FW
	7: FE
	'''
	num: 'Point'
	'''
	a repeating set of sites that create the row (DO num.x BY num.y)
	'''
	step: 'Point'
	'''
	the spacing between sites in horizontal and vertical rows (STEP step.x step.y)
	'''
	props: Dict[str, Any]
	'''
	user-defined properties
	'''

	def __init__(self, swig_ref: LEFDEF.DEFRow = None, design: 'DEFDesign' = None):
		"""
		create a row in the specified design

		:param swig_ref: imported DEFRow from LEFDEF C++ library, if not specified, create empty object
		:param design: DEFDesign which this DEFRow belongs to. DEFDesign should have a valid DEF as member, and the DEF should have a valid LEF as member which has LEF site definition
		"""
		if swig_ref is None:
			self.name = ''
			self.design = None
			self.site = None
			self.origin = Point(x=0, y=0, point_type=int)
			self.orientation = -1
			self.num = Point(x=0, y=0, point_type=int)
			self.step = Point(x=0, y=0, point_type=int)
		else:
			self.name = swig_ref.name
			self.design = design
			if design is not None:
				self.site = design.DEF.LEF.sites[swig_ref.site_name] if swig_ref.site_name in design.DEF.LEF.sites else None
			else:
				self.site = None
			self.origin = Point(swig_ref=swig_ref.origin)
			self.orientation = swig_ref.orientation
			self.num = Point(swig_ref=swig_ref.num)
			self.step = Point(swig_ref=swig_ref.step)
		self.props = {}

	def __setitem__(self, key, value):
		self.props[key] = value

	def __getitem__(self, item):
		return self.props[item]

	def __contains__(self, item):
		if item in self.props:
			return True
		else:
			return False

	def export(self) -> LEFDEF.DEFRow:
		"""
		export the row to LEFDEF C++ library

		:return: DEFRow in LEFDEF C++ library
		"""
		targ = LEFDEF.DEFRow()
		targ.name = self.name
		targ.site_name = self.site.name if self.site is not None else ''
		targ.origin = self.origin.export()
		targ.orientation = self.orientation
		targ.num = self.num.export()
		targ.step = self.step.export()
		return targ

	def copy(self, design: 'DEFDesign') -> 'DEFRow':
		"""
		copy the object

		:param design: DEFDesign which this DEFRow belongs to. DEFDesign should have a valid DEF as member, and the DEF should have a valid LEF as member which has LEF site definition
		:return: copied object
		"""
		cp = DEFRow()
		cp.name = self.name
		cp.design = design
		cp.site = design.DEF.LEF.sites[self.site.name] if self.site is not None and self.site.name in design.DEF.LEF.sites else None
		cp.origin = self.origin.copy()
		cp.orientation = self.orientation
		cp.num = self.num.copy()
		cp.step = self.step.copy()
		cp.props = self.props.copy()
		return cp

	def fit_width(self, boundary: 'Rect') -> bool:
		"""
		shorten or lengthen the width of the row to fit to the given rect. if there is no site in this row after fitting, it will return False. otherwise, True.
		it only supports the row with numY = 1

		:param boundary: rectangle to fit the row
		:return: if there is no site in this row after fitting, it will return False. otherwise, True
		"""
		if self.num.y != 1:
			logger.error('fitting row is only supported when numY = 1. the row is unchanged')
			return True
		else:
			if self.origin.y < boundary.ll.y or boundary.ur.y < self.origin.y + self.site.height * self.design.dbUnits:
				return False
			else:
				self.origin.x = int(int(boundary.ll.x / (self.site.width * self.design.dbUnits)) * (self.site.width * self.design.dbUnits))
				row_urx = int(int(boundary.ur.x / (self.site.width * self.design.dbUnits) - 1) * (self.site.width * self.design.dbUnits))
				self.num.x = int(int((row_urx - self.origin.x) / (self.site.width * self.design.dbUnits)))
				if self.num.x < 1:
					return False
			return True


class DEFTrack:
	"""
	represents a track in a design
	"""
	direction: int
	'''
	direction of the track
	-1: NULL
	0: X
	1: Y
	'''
	start: int
	'''
	the location of the first track defined
	'''
	numTracks: int
	'''
	number of tracks to create for the grid
	'''
	space: int
	'''
	spacing between the tracks
	'''
	layers: List['LEFLayer']
	'''
	routing layer used for the tracks
	'''
	props: Dict[str, Any]
	'''
	user-defined properties
	'''

	def __init__(self, swig_ref: LEFDEF.DEFTrack = None, design: 'DEFDesign' = None):
		"""
		create a track in the specified design

		:param swig_ref: imported DEFTrack from LEFDEF C++ library, if not specified, create empty object
		:param design: DEFDesign which this DEFTrack belongs to. DEFDesign should have a valid DEF as member, and the DEF should have a valid LEF as member which has full list of LEF layers
		"""
		if swig_ref is None or design is None:
			self.direction = -1
			self.start = 0
			self.numTracks = 0
			self.space = 0
			self.layers = []
		else:
			self.direction = swig_ref.direction
			self.start = swig_ref.start
			self.numTracks = swig_ref.numTracks
			self.space = swig_ref.space
			self.layers = []
			if design is not None:
				for layer_name in list(swig_ref.layer_names):
					if layer_name in design.DEF.LEF.layers:
						self.layers.append(design.DEF.LEF.layers[layer_name])
				self.layers = [design.DEF.LEF.layers[layer_name] for layer_name in list(swig_ref.layer_names)]
		self.props = {}

	def __setitem__(self, key, value):
		self.props[key] = value

	def __getitem__(self, item):
		return self.props[item]

	def __contains__(self, item):
		if item in self.props:
			return True
		else:
			return False

	def export(self) -> LEFDEF.DEFTrack:
		"""
		export the track to LEFDEF C++ library

		:return: DEFTrack in LEFDEF C++ library
		"""
		targ = LEFDEF.DEFTrack()
		targ.direction = self.direction
		targ.start = self.start
		targ.numTracks = self.numTracks
		targ.space = self.space
		targ.layer_names = LEFDEF.VecStr([layer.name for layer in self.layers])
		return targ

	def copy(self, design: 'DEFDesign') -> 'DEFTrack':
		"""
		copy the object

		:param design: DEFDesign which this DEFTrack belongs to. DEFDesign should have a valid DEF as member, and the DEF should have a valid LEF as member which has full list of LEF layers
		:return: copied object
		"""
		cp = DEFTrack()
		cp.direction = self.direction
		cp.start = self.start
		cp.numTracks = self.numTracks
		cp.space = self.space
		for layer in self.layers:
			if layer.name in design.DEF.LEF.layers:
				cp.layers.append(design.DEF.LEF.layers[layer.name])
		cp.props = self.props.copy()
		return cp


class DEFGCellGrid:
	"""
	create GCellGrid in a design
	"""
	direction: int
	'''
	direction of the GCellGrid
	-1: NULL
	0: X
	1: Y
	'''
	start: int
	'''
	the location of the first GCellGrid defined
	'''
	numColsRows: int
	'''
	number of columns/rows in the grid
	'''
	space: int
	'''
	spacing between tracks
	'''
	props: Dict[str, Any]
	'''
	user-defined properties
	'''

	def __init__(self, swig_ref: LEFDEF.DEFGCellGrid = None):
		"""
		create a GCellGrid

		:param swig_ref: imported DEFGCellGrid from LEFDEF C++ library, if not specified, create empty object
		"""
		if swig_ref is None:
			self.direction = -1
			self.start = 0
			self.numColsRows = 0
			self.space = 0
		else:
			self.direction = swig_ref.direction
			self.start = swig_ref.start
			self.numColsRows = swig_ref.numColsRows
			self.space = swig_ref.space
		self.props = {}

	def __setitem__(self, key, value):
		self.props[key] = value

	def __getitem__(self, item):
		return self.props[item]

	def __contains__(self, item):
		if item in self.props:
			return True
		else:
			return False

	def export(self) -> LEFDEF.DEFGCellGrid:
		"""
		export the GCellGrid to LEFDEF C++ library

		:return: DEFGCellGrid in LEFDEF C++ library
		"""
		targ = LEFDEF.DEFGCellGrid()
		targ.direction = self.direction
		targ.start = self.start
		targ.numColsRows = self.numColsRows
		targ.space = self.space
		return targ

	def copy(self) -> 'DEFGCellGrid':
		"""
		copy the object

		:return: copied object
		"""
		cp = DEFGCellGrid()
		cp.direction = self.direction
		cp.start = self.start
		cp.numColsRows = self.numColsRows
		cp.space = self.space
		cp.props = self.props.copy()
		return cp


class DEFViaRule:
	"""
	represents a via rule definition in a design
	"""
	name: str
	'''
	name of the via rule
	'''
	viarule: Union['LEFViaRule', None]
	'''
	LEF via rule for this via rule
	'''
	cutSize: Point
	'''
	cut size of this via rule
	'''
	cutLayer: Union['LEFLayer', None]
	'''
	cut layer of this via rule
	'''
	botRoutingLayer: Union['LEFLayer', None]
	'''
	bottom routing layer of this via rule
	'''
	topRoutingLayer: Union['LEFLayer', None]
	'''
	top routing layer of this via rule
	'''
	cutSpacing: Point
	'''
	cut spacing of this via rule
	'''
	botEnc: Point
	'''
	bottom routing layer enclosure of this via rule
	'''
	topEnc: Point
	'''
	top routing layer enclosure of this via rule
	'''
	rowcol: Point
	'''
	the number of cut rows and columns that make up the cut array
	'''
	props: Dict[str, Any]
	'''
	user-defined properties
	'''

	def __init__(self, swig_ref: LEFDEF.DEFViaRule = None, design: 'DEFDesign' = None):
		"""
		create a via rule

		:param swig_ref: imported DEFViaRule from LEFDEF C++ library, if not specified, create empty object
		:param design: DEFDesign which this DEFViaRule belongs to. DEFDesign should have a valid DEF as member, and the DEF should have a valid LEF as member which has full list of LEF layers
		"""
		if swig_ref is None:
			self.name = ''
			self.viarule = None
			self.cutSize = Point(x=0, y=0, point_type=int)
			self.cutLayer = None
			self.botRoutingLayer = None
			self.topRoutingLayer = None
			self.cutSpacing = Point(x=0, y=0, point_type=int)
			self.botEnc = Point(x=0, y=0, point_type=int)
			self.topEnc = Point(x=0, y=0, point_type=int)
			self.rowcol = Point(x=1, y=1, point_type=int)
		else:
			self.name = swig_ref.name
			self.viarule = design.DEF.LEF.viarules[swig_ref.viarule_name]
			self.cutSize = Point(swig_ref=swig_ref.cutSize)
			self.cutLayer = design.DEF.LEF.layers[swig_ref.cutLayer_name] if swig_ref.cutLayer_name in design.DEF.LEF.layers else None
			self.botRoutingLayer = design.DEF.LEF.layers[swig_ref.botRoutingLayer_name] if swig_ref.botRoutingLayer_name in design.DEF.LEF.layers else None
			self.topRoutingLayer = design.DEF.LEF.layers[swig_ref.topRoutingLayer_name] if swig_ref.topRoutingLayer_name in design.DEF.LEF.layers else None
			self.cutSpacing = Point(swig_ref=swig_ref.cutSpacing)
			self.botEnc = Point(swig_ref=swig_ref.botEnc)
			self.topEnc = Point(swig_ref=swig_ref.topEnc)
			self.rowcol = Point(swig_ref=swig_ref.rowcol)
		self.props = {}

	def __setitem__(self, key, value):
		self.props[key] = value

	def __getitem__(self, item):
		return self.props[item]

	def __contains__(self, item):
		if item in self.props:
			return True
		else:
			return False

	def export(self) -> LEFDEF.DEFViaRule:
		"""
		export the DEF via rule to LEFDEF C++ library

		:return: DEFViaRule in LEFDEF C++ library
		"""
		targ = LEFDEF.DEFViaRule()
		targ.name = self.name
		targ.viarule_name = self.viarule.name if self.viarule is not None else ''
		targ.cutSize = self.cutSize.export()
		targ.cutLayer_name = self.cutLayer.name if self.cutLayer is not None else ''
		targ.botRoutingLayer_name = self.botRoutingLayer.name if self.botRoutingLayer is not None else ''
		targ.topRoutingLayer_name = self.topRoutingLayer.name if self.topRoutingLayer is not None else ''
		targ.cutSpacing = self.cutSpacing.export()
		targ.botEnc = self.botEnc.export()
		targ.topEnc = self.topEnc.export()
		targ.rowcol = self.rowcol.export()
		return targ

	def copy(self, design: 'DEFDesign' = None) -> 'DEFViaRule':
		"""
		copy the object

		:param design: DEFDesign which this DEFViaRule belongs to. DEFDesign should have a valid DEF as member, and the DEF should have a valid LEF as member which has full list of LEF layers
		:return: copied object
		"""
		cp = DEFViaRule()
		cp.name = self.name
		cp.viarule = design.DEF.LEF.viarules[self.viarule.name] if self.viarule is not None and self.viarule.name in design.DEF.LEF.viarules else None
		cp.cutSize = self.cutSize.copy()
		cp.cutLayer = design.DEF.LEF.layers[self.cutLayer.name] if self.cutLayer is not None and self.cutLayer.name in design.DEF.LEF.layers else None
		cp.botRoutingLayer = design.DEF.LEF.layers[self.botRoutingLayer.name] if self.botRoutingLayer is not None and self.botRoutingLayer.name in design.DEF.LEF.layers else None
		cp.topRoutingLayer = design.DEF.LEF.layers[self.topRoutingLayer.name] if self.topRoutingLayer is not None and self.topRoutingLayer.name in design.DEF.LEF.layers else None
		cp.cutSpacing = self.cutSpacing.copy()
		cp.botEnc = self.botEnc.copy()
		cp.topEnc = self.topEnc.copy()
		cp.rowcol = self.rowcol.copy()
		cp.props = self.props.copy()
		return cp


class DEFVia:
	"""
	represents a via instance used in a design
	"""
	via: Union['LEFVia', 'DEFViaRule', None]
	'''
	LEF or DEF via used for this via instance
	'''
	loc: 'Point'
	'''
	location of the via instance
	'''
	props: Dict[str, Any]
	'''
	user-defined properties
	'''

	def __init__(self, swig_ref: LEFDEF.DEFVia = None, design: 'DEFDesign' = None):
		"""
		create a via instance in the specified design

		:param swig_ref: imported DEFVia from LEFDEF C++ library, if not specified, create empty object
		:param design: DEFDesign which this DEFVia belongs to. DEFDesign should have a valid DEF as member, and the DEF should have a valid LEF as member which has LEF via definitions
		"""
		if swig_ref is None:
			self.via = None
			self.loc = Point(x=0, y=0, point_type=int)
		else:
			if design is not None:
				if swig_ref.via_name in design.DEF.LEF.vias:
					self.via = design.DEF.LEF.vias[swig_ref.via_name]
				elif swig_ref.via_name in design.vias:
					self.via = design.vias[swig_ref.via_name]
				elif swig_ref.via_name in design.viarules:
					self.via = design.viarules[swig_ref.via_name]
				else:
					self.via = None
			else:
				self.via = None
			self.loc = Point(swig_ref=swig_ref.loc)
		self.props = {}

	def __setitem__(self, key, value):
		self.props[key] = value

	def __getitem__(self, item):
		return self.props[item]

	def __contains__(self, item):
		if item in self.props:
			return True
		else:
			return False

	def export(self) -> LEFDEF.DEFVia:
		"""
		export the via instance to LEFDEF C++ library

		:return: DEFVia in LEFDEF C++ library
		"""
		targ = LEFDEF.DEFVia()
		targ.via_name = self.via.name if self.via is not None else ''
		targ.loc = self.loc.export()
		return targ

	def copy(self, design: 'DEFDesign') -> 'DEFVia':
		"""
		copy the object

		:param design: DEFDesign which this DEFVia belongs to. DEFDesign should have a valid DEF as member, and the DEF should have a valid LEF as member which has LEF via definitions
		:return: copied object
		"""
		cp = DEFVia()
		if self.via is None:
			cp.via = None
		elif self.via.name in design.DEF.LEF.vias:
			cp.via = design.DEF.LEF.vias[self.via.name]
		elif self.via.name in design.vias:
			cp.via = design.vias[self.via.name]
		elif self.via.name in design.viarules:
			cp.via = design.viarules[self.via.name]
		else:
			cp.via = None
		cp.loc = self.loc.copy()
		cp.props = self.props.copy()
		return cp


class DEFComponent:
	"""
	represents a component in a design
	"""
	name: str
	'''
	name of the component
	'''
	design: Union['DEFDesign', None]
	'''
	design that this component belongs to
	'''
	macro: Union['LEFMacro', None]
	'''
	LEF macro of the component
	'''
	eeq: str
	'''
	EEQ of this component
	'''
	source: int
	'''
	source of this component
	0: netlist
	1: dist
	2: timing
	3: user
	'''
	pStatus: int
	'''
	placement status
	-1: NULL
	0: fixed
	1: cover
	2: placed
	3: unplaced
	'''
	loc: 'Point'
	'''
	location of the component
	'''
	orientation: int
	'''
	orientation of the component
	-1: NULL
	0: N
	1: W
	2: S
	3: E
	4: FN
	5: FW
	6: FS
	7: FE
	'''
	weight: int
	'''
	weight of the component
	'''
	pin2net: Dict[str, 'DEFNet']
	'''
	pin name to net which the pin is connected to
	'''
	props: Dict[str, Any]
	'''
	user-defined properties
	'''

	def __init__(self, swig_ref: LEFDEF.DEFComponent = None, design: 'DEFDesign' = None, verilog_comp = None):
		"""
		create a component in the specified design

		:param swig_ref: imported DEFComponent from LEFDEF C++ library, if not specified, create empty object
		:param design: DEFDesign which this DEFComponent belongs to. DEFDesign should have a valid DEF as member, and the DEF should have a valid LEF as member which has macro definitions
		"""
		if swig_ref is None and verilog_comp is None:
			self.name = ''
			self.design = design
			self.macro = None
			self.eeq = ''
			self.source = 0
			self.pStatus = -1
			self.loc = Point(x=0, y=0, point_type=int)
			self.orientation = -1
			self.weight = 0
			self.pin2net = {}
		elif swig_ref is None and verilog_comp is not None:
			self.name = verilog_comp.instance_name
			self.design = design
			# self.macro = design.DEF.LEF.macros[verilog_comp.module_name] if verilog_comp.module_name in design.DEF.LEF.macros else None
			if verilog_comp.module_name in design.DEF.LEF.macros:
				self.macro = design.DEF.LEF.macros[verilog_comp.module_name] if verilog_comp.module_name in design.DEF.LEF.macros else None
			else:
				self.macro = verilog_comp.module_name
				design.DEF.designs[verilog_comp.module_name].module_hier.append(design.name)
			self.eeq = ''
			self.source = 0
			self.pStatus = -1
			self.loc = Point(x=0, y=0, point_type=int)
			self.orientation = -1
			self.weight = 0
			self.pin2net = {}
		else:
			self.name = swig_ref.name
			self.design = design
			self.macro = design.DEF.LEF.macros[swig_ref.macro_name] if swig_ref.macro_name in design.DEF.LEF.macros else None
			self.eeq = swig_ref.eeq
			self.source = swig_ref.source
			self.pStatus = swig_ref.pStatus
			self.loc = Point(swig_ref=swig_ref.loc)
			self.orientation = swig_ref.orientation
			self.weight = swig_ref.weight
			self.pin2net = {}
			# pin2net is created in DEFNet init function after all nets are read
		self.props = {}

	def __setitem__(self, key, value):
		self.props[key] = value

	def __getitem__(self, item):
		return self.props[item]

	def __contains__(self, item):
		if item in self.props:
			return True
		else:
			return False

	def export(self) -> LEFDEF.DEFComponent:
		"""
		export the component to LEFDEF C++ library

		:return: DEFComponent in LEFDEF C++ library
		"""
		targ = LEFDEF.DEFComponent()
		targ.name = self.name
		targ.macro_name = self.macro.name if self.macro is not None else ''
		targ.eeq = self.eeq
		targ.source = self.source
		targ.pStatus = self.pStatus
		targ.loc = self.loc.export()
		targ.orientation = self.orientation
		targ.weight = self.weight
		targ.pin2net_name = LEFDEF.MapStrStr({pin_name: net_info.name for pin_name, net_info in self.pin2net.items()})
		return targ

	def copy(self, design: 'DEFDesign') -> 'DEFComponent':
		"""
		copy the object

		:param design: DEFDesign which this DEFComponent belongs to. DEFDesign should have a valid DEF as member, and the DEF should have a valid LEF as member which has macro definitions
		:return: copied object
		"""
		cp = DEFComponent()
		cp.name = self.name
		cp.design = design
		cp.macro = design.DEF.LEF.macros[self.macro.name] if self.macro is not None and self.macro.name in design.DEF.LEF.macros else None
		cp.eeq = self.eeq
		cp.source = self.source
		cp.pStatus = self.pStatus
		cp.loc = self.loc.copy()
		cp.orientation = self.orientation
		cp.weight = self.weight
		cp.pin2net = {}
		# pin2net is created in DEFNet init function after all nets are read
		return cp

	def change_macro(self, macro_map: Dict[str, str], new_lef: 'LEF'):
		"""
		change macro based on macro_map. the resulting macro will point macros in new_lef

		:param macro_map: current macro name:new macro name map
		:param new_lef: LEF object which contains all the new macros
		"""
		self.macro = new_lef.macros[macro_map[self.macro.name]] if self.macro is not None and self.macro.name in macro_map and macro_map[self.macro.name] in new_lef.macros else None

	def is_shifted_by_row_splitting(self, tier_num: int) -> bool:
		"""
		check whether the component location is shifted due to row splitting

		:param tier_num: tier number which this component is assigned
		:return: True if component should be (or is) shifted. Otherwise, false
		"""
		return (tier_num % 2 == 0 and self.orientation % 4 == 2) or (tier_num % 2 == 1 and self.orientation % 4 == 0)

	def get_shape(self) -> 'Shape':
		"""
		get the component shape in the design (layer info will be None)

		:return: shape of the component
		"""
		comp_shape = Shape(shape_type=0)
		comp_shape.rect = Rect(llx=self.loc.x,
							   lly=self.loc.y,
							   urx=self.loc.x+int(self.macro.width*self.design.dbUnits),
							   ury=self.loc.y+int(self.macro.height*self.design.dbUnits),
							   rect_type=int
							   )
		return comp_shape


class DEFPin:
	"""
	represents a pin (port) of the specified design
	"""
	name: str
	'''
	name of the pin
	'''
	design: Union['DEFDesign', None]
	'''
	design that this pin belongs to
	'''
	net: Union['DEFNet', None]
	'''
	net which the pin is connected to
	'''
	net_name: str
	'''
	name of the nets which the pin is connected to. it is needed because net object is created after pin object is created. normally most of connection between pin and net can be covered by net init function only, but for special nets, they do not explicitly covers connection between pins and special nets, and their connections are covered in pins section only (DEFDesign init function)
	'''
	isSpecial: bool
	'''
	whether it is a pin for special net or not
	'''
	direction: int
	'''
	direction of the pin
	-1: NULL
	0: input
	1: output
	2: inout
	3: feedthru
	'''
	supplySensitivity: str
	'''
	if this pin is connected to a tie-high connection, it should connect to the same net to which this pin name is connected
	'''
	groundSensitivity: str
	'''
	if this pin is connected to a tie-low connection, it should connect to the same net to which this pin name is connected
	'''
	type: int
	'''
	pin type
	0: ANALOG
	1: CLOCK
	2: GROUND
	3: POWER
	4: RESET
	5: SCAN
	6: SIGNAL
	7: TIEOFF	
	'''
	shapes: List['Shape']
	'''
	list of shapes for the pin
	'''
	pStatus: int
	'''
	placement status
	-1: NULL
	0: cover
	1: fixed
	2: placed
	'''
	loc: Point
	'''
	location of the pin
	'''
	orientation: int
	'''
	orientation of the pin
	-1: NULL
	0: N
	1: S
	2: W
	3: E
	4: FN
	5: FS
	6: FW
	7: FE
	'''
	props: Dict[str, Any]
	'''
	user-defined properties
	'''

	def __init__(self, swig_ref: LEFDEF.DEFPin = None, design: 'DEFDesign' = None, verilog_pins = None):
		"""
		create a pin (port) in the specified design

		:param swig_ref: imported DEFBlkg from LEFDEF C++ library, if not specified, create empty object
		:param design: DEFDesign which this DEFBlkg belongs to. DEFDesign should have a valid DEF as member, and the DEF should have a valid LEF as member which has full list of LEF layers
		"""
		if swig_ref is None and verilog_pins is None:
			self.name = ''
			self.design = None
			self.net = None
			self.net_name = ''
			self.isSpecial = False
			self.direction = -1
			self.supplySensitivity = ''
			self.groundSensitivity = ''
			self.type = 6
			self.shapes = []
			self.pStatus = -1
			self.loc = Point(x=0, y=0, point_type=int)
			self.orientation = -1
		elif swig_ref is None and verilog_pins is not None:
			verilog_obj = verilog_pins[0]
			pin_name = verilog_pins[1]
			self.name = pin_name
			self.design = design
			self.net = None
			self.net_name = ''
			self.isSpecial = False
			self.direction = -1
			self.supplySensitivity = ''
			self.groundSensitivity = ''
			self.type = 6
			self.shapes = []
			self.pStatus = -1
			self.loc = Point(x=0, y=0, point_type=int)
			self.orientation = -1
		else:
			self.name = swig_ref.name
			self.design = design
			self.net = None
			# net is created in DEFNet init function after all nets are read
			self.net_name = swig_ref.net_name
			self.isSpecial = swig_ref.isSpecial
			self.direction = swig_ref.direction
			self.supplySensitivity = swig_ref.supplySensitivity
			self.groundSensitivity = swig_ref.groundSensitivity
			self.type = swig_ref.type
			if design is not None:
				self.shapes = [Shape(shape, design.DEF.LEF.layers) for shape in list(swig_ref.shapes)]
			else:
				self.shapes = [Shape(shape) for shape in list(swig_ref.shapes)]
			self.pStatus = swig_ref.pStatus
			self.loc = Point(swig_ref=swig_ref.loc)
			self.orientation = swig_ref.orientation
		self.props = {}

	def __setitem__(self, key, value):
		self.props[key] = value

	def __getitem__(self, item):
		return self.props[item]

	def __contains__(self, item):
		if item in self.props:
			return True
		else:
			return False

	def export(self) -> LEFDEF.DEFPin:
		"""
		export the pin to LEFDEF C++ library

		:return: DEFPin in LEFDEF C++ library
		"""
		targ = LEFDEF.DEFPin()
		targ.name = self.name
		targ.net_name = self.net.name if self.net is not None else self.net_name
		targ.isSpecial = self.isSpecial
		targ.direction = self.direction
		targ.supplySensitivity = self.supplySensitivity
		targ.groundSensitivity = self.groundSensitivity
		targ.type = self.type
		targ.shapes = LEFDEF.VecShape([shape.export() for shape in self.shapes])
		targ.pStatus = self.pStatus
		targ.loc = self.loc.export()
		targ.orientation = self.orientation
		return targ

	def copy(self, design: 'DEFDesign') -> 'DEFPin':
		"""
		copy the object

		:param design: DEFDesign which this DEFPin belongs to. DEFDesign should have a valid DEF as member, and the DEF should have a valid LEF as member which has full list of LEF layers
		:return: copied object
		"""
		cp = DEFPin()
		cp.name = self.name
		cp.design = design
		cp.net = None
		# net is created in DEFNet init function after all nets are read
		cp.net_name = self.net_name
		cp.isSpecial = self.isSpecial
		cp.direction = self.direction
		cp.supplySensitivity = self.supplySensitivity
		cp.groundSensitivity = self.groundSensitivity
		cp.type = self.type
		cp.shapes = [shape.copy(design.DEF.LEF.layers) for shape in self.shapes]
		cp.pStatus = self.pStatus
		cp.loc = self.loc.copy()
		cp.orientation = self.orientation
		cp.props = self.props.copy()
		return cp

	def change_layer(self, layer_map: Dict[str, str], new_lef: Union['LEF', 'LEFNonDefaultRule']):
		"""
		change LEF layer based on layer_map. the resulting pin will point layers in new_lef

		:param layer_map: current layer name:new layer name map
		:param new_lef: LEF object which contains all the new layers
		"""
		for shape in self.shapes:
			shape.change_layers(layer_map, new_lef.layers)

	def get_pin_shapes_in_design(self) -> List['Shape']:
		"""
		get shapes of this pin reflecting the pin location

		:return: pin shapes in design
		"""
		shapes_in_design = []
		for shape in self.shapes:
			shape_in_design = shape.copy(self.design.DEF.LEF.layers)
			if self.orientation == 1:
				# W (R90)
				shape_in_design.R90()
			elif self.orientation == 2:
				# S (R180)
				shape_in_design.R180()
			elif self.orientation == 3:
				# E (R270)
				shape_in_design.R270()
			elif self.orientation == 4:
				# FN (flip y axis)
				shape_in_design.MY()
			elif self.orientation == 5:
				# FW (flip x axis and R90)
				shape_in_design.MX()
				shape_in_design.R90()
			elif self.orientation == 6:
				# FS (flip x axis)
				shape_in_design.MX()
			elif self.orientation == 7:
				# FE (flip y axis and R 90)
				shape_in_design.MY()
				shape_in_design.R90()
			shape_in_design.move(self.loc.x, self.loc.y)
			shapes_in_design.append(shape_in_design)
		return shapes_in_design


class DEFComponentPin:
	"""
	represents a pin of a component
	"""
	design: Union['DEFDesign', None]
	'''
	design that this component pin belongs to
	'''
	comp: Union['DEFComponent', None]
	'''
	component that the pin belongs to
	'''
	pin: Union['LEFMacroPin', None]
	'''
	the corresponding pin of LEF macro
	'''
	props: Dict[str, Any]
	'''
	user-defined properties
	'''

	def __init__(self, swig_ref: LEFDEF.DEFComponentPin = None, design: 'DEFDesign' = None, verilog_compPin = None):
		"""
		create a pin of a component in the specified design

		:param swig_ref: imported DEFComponentPin from LEFDEF C++ library, if not specified, create empty object
		:param design: DEFDesign which this DEFComponentPin belongs to. DEFDesign should have component definitions
		"""
		if swig_ref is None and verilog_compPin is None:
			self.design = None
			self.comp = None
			self.pin = None
		elif swig_ref is None and verilog_compPin is not None:
			self.design = design
			self.comp = design.components[verilog_compPin.instance]
			# if design.components[verilog_compPin.instance].macro is not None:
			if design.components[verilog_compPin.instance].macro not in design.sub_module:
				self.pin = design.components[verilog_compPin.instance].macro.pins[verilog_compPin.pin]
			else:
				# self.pin = design.DEF.designs[verilog_compPin.instance].verilog_module.port_list
				self.pin = design.DEF.designs[design.components[verilog_compPin.instance].macro].verilog_module.port_list
		else:
			self.design = design
			# handling wildcards for component name in net connections
			if swig_ref.comp_name == '*':
				self.comp = DEFComponent()
				self.comp.name = '*'
				self.pin = LEFMacroPin()
				self.pin.name = swig_ref.pin_name
			else:
				if design is not None:
					self.comp = design.components[swig_ref.comp_name]
					self.pin = design.components[swig_ref.comp_name].macro.pins[swig_ref.pin_name]
				else:
					self.comp = None
					self.pin = None
		self.props = {}

	def __setitem__(self, key, value):
		self.props[key] = value

	def __getitem__(self, item):
		return self.props[item]

	def __contains__(self, item):
		if item in self.props:
			return True
		else:
			return False

	def export(self) -> LEFDEF.DEFComponentPin:
		"""
		export the pin of the component to LEFDEF C++ library

		:return: DEFComponentPin in LEFDEF C++ library
		"""
		targ = LEFDEF.DEFComponentPin()
		targ.comp_name = self.comp.name if self.comp is not None else ''
		targ.pin_name = self.pin.name if self.pin is not None else ''
		return targ

	def copy(self, design: 'DEFDesign') -> 'DEFComponentPin':
		"""
		copy the object

		:param design: DEFDesign which this DEFComponentPin belongs to. DEFDesign should have component definitions
		:return: copied object
		"""
		cp = DEFComponentPin()
		cp.design = design
		# handling wildcards for component name in net connections
		if self.comp is None:
			cp.comp = None
		elif self.comp.name == '*':
			cp.comp = self.comp.copy(design)
		else:
			cp.comp = design.components[self.comp.name] if self.comp.name in design.components else None
		if self.pin is None:
			cp.pin = None
		elif self.comp.name == '*':
			cp.pin = self.pin.copy(design.DEF.LEF)
		else:
			cp.pin = design.components[self.comp.name].macro.pins[self.pin.name] if self.comp.name in design.components and self.pin.name in design.components[self.comp.name].macro.pins else None
		cp.props = self.props.copy()
		return cp

	def get_comp_pin_shapes_in_design(self) -> List['Shape']:
		"""
		get shapes of component pin reflecting the component location

		:return: component pin shapes in design
		"""
		shapes_in_design = []
		macro_height = self.comp.macro.height - self.comp.macro.origin.y
		macro_width = self.comp.macro.width - self.comp.macro.origin.x
		for shape in self.pin.shapes:
			shape_in_design = shape.copy(self.design.DEF.LEF.layers)
			if self.comp.orientation == 1:
				# W (R90)
				shape_in_design.R90()
				shape_in_design.move(macro_height, 0)
			elif self.comp.orientation == 2:
				# S (R180)
				shape_in_design.R180()
				shape_in_design.move(macro_width, macro_height)
			elif self.comp.orientation == 3:
				# E (R270)
				shape_in_design.R270()
				shape_in_design.move(0, macro_width)
			elif self.comp.orientation == 4:
				# FN (flip y axis)
				shape_in_design.MY()
				shape_in_design.move(macro_width, 0)
			elif self.comp.orientation == 5:
				# FW (flip x axis and R90)
				shape_in_design.MX()
				shape_in_design.move(0, macro_height)
				shape_in_design.R90()
				shape_in_design.move(macro_height, 0)
			elif self.comp.orientation == 6:
				# FS (flip x axis)
				shape_in_design.MX()
				shape_in_design.move(0, macro_height)
			elif self.comp.orientation == 7:
				# FE (flip y axis and R 90)
				shape_in_design.MY()
				shape_in_design.move(macro_width, 0)
				shape_in_design.R90()
				shape_in_design.move(macro_height, 0)
			shape_in_design.scale(self.design.dbUnits)
			shape_in_design.to_integer()
			shape_in_design.move(self.comp.loc.x, self.comp.loc.y)
			shapes_in_design.append(shape_in_design)
		return shapes_in_design


class DEFPath:
	"""
	represents a path of wires of nets in the specified design
	"""
	design: Union['DEFDesign', None]
	'''
	design that this path belongs to
	'''
	layer: Union['LEFLayer', None]
	'''
	LEF layer that this path is on
	'''
	shape: int
	'''
	shape of the path
	-1: NULL
	0: ring
	1: padring
	2: blockring
	3: stripe
	4: followpin
	5: iowire
	6: corewire
	7: blockwire
	8: fillwire
	9: blockagewire
	10: drcfill
	'''
	isVirtual: List[bool]
	'''
	whether pts with the same index is virtual point or not
	'''
	pts: List['Point']
	'''
	list of points that this path go through
	'''
	exts: List[int]
	'''
	list of extension of each point in pts
	'''
	isRect: List[bool]
	'''
	whether pts with the same index should be replaced with RECT	
	'''
	rects: List['Rect']
	'''
	RECT values (rectangle containing the detal values from the previous routing point)
	'''
	vias: List['DEFVia']
	'''
	list of vias in this path
	'''
	props: Dict[str, Any]
	'''
	user-defined properties
	'''

	def __init__(self, swig_ref: LEFDEF.DEFPath = None, design: 'DEFDesign' = None):
		"""
		create a path of wires of nets in the specified design

		:param swig_ref: imported DEFPath from LEFDEF C++ library, if not specified, create empty object
		:param design: DEFDesign which this DEFPath belongs to. DEFDesign should have a valid DEF as member, and the DEF should have a valid LEF as member which has full list of LEF layers
		"""
		if swig_ref is None:
			self.design = None
			self.layer = None
			self.shape = -1
			self.isVirtual = []
			self.pts = []
			self.exts = []
			self.isRect = []
			self.rects = []
			self.vias = []
		else:
			self.design = design
			if design is not None:
				self.layer = design.DEF.LEF.layers[swig_ref.layer_name] if swig_ref.layer_name in design.DEF.LEF.layers else None
			else:
				self.layer = None
			self.shape = swig_ref.shape
			self.isVirtual = [False if isVirtual == 0 else True for isVirtual in swig_ref.isVirtual]
			self.pts = [Point(swig_ref=pt) for pt in list(swig_ref.pts)]
			self.exts = list(swig_ref.exts)
			self.isRect = [False if isRect == 0 else True for isRect in swig_ref.isRect]
			self.rects = [Rect(swig_ref=rect) for rect in list(swig_ref.rects)]
			if design is not None:
				self.vias = [DEFVia(via, design) for via in list(swig_ref.vias)]
			else:
				self.vias = [DEFVia(via) for via in list(swig_ref.vias)]
		self.props = {}

	def __setitem__(self, key, value):
		self.props[key] = value

	def __getitem__(self, item):
		return self.props[item]

	def __contains__(self, item):
		if item in self.props:
			return True
		else:
			return False

	def export(self) -> LEFDEF.DEFPath:
		"""
		export the path of wires of nets to LEFDEF C++ library

		:return: DEFPath in LEFDEF C++ library
		"""
		targ = LEFDEF.DEFPath()
		targ.layer_name = self.layer.name if self.layer is not None else ''
		targ.isVirtual = LEFDEF.VecInt([0 if not isVirtual else 1 for isVirtual in self.isVirtual])
		targ.pts = LEFDEF.VecIntPt([pt.export() for pt in self.pts])
		targ.exts = LEFDEF.VecInt(self.exts)
		targ.isRect = LEFDEF.VecInt([0 if not isRect else 1 for isRect in self.isRect])
		targ.rects = LEFDEF.VecIntRect([rect.export() for rect in self.rects])
		targ.vias = LEFDEF.VecDEFVia([via.export() for via in self.vias])
		return targ

	def copy(self, design: 'DEFDesign') -> 'DEFPath':
		"""
		copy the object

		:param design: DEFDesign which this DEFPath belongs to. DEFDesign should have a valid DEF as member, and the DEF should have a valid LEF as member which has full list of LEF layers
		:return: copied object
		"""
		cp = DEFPath()
		cp.design = design
		cp.layer = design.DEF.LEF.layers[self.layer.name] if self.layer is not None and self.layer.name in design.DEF.LEF.layers else None
		cp.isVirtual = self.isVirtual[:]
		cp.pts = [pt.copy() for pt in self.pts]
		cp.exts = self.exts[:]
		cp.isRect = self.isRect[:]
		cp.rects = [rect.copy() for rect in self.rects]
		cp.vias = [via.copy(design) for via in self.vias]
		cp.props = self.props.copy()
		return cp

	def get_routing_shape(self) -> List['Shape']:
		"""
		get shapes of routing (metal) of this path (represented by pts)

		:return: routing shapes of this path
		"""
		shapes = []
		prev_pt_idx = -1
		for i, pt in enumerate(self.pts):
			if prev_pt_idx != -1:
				if self.isRect[i]:
					shape = Shape(shape_type=0)
					shape.rect = Rect(llx=int(self.pts[prev_pt_idx].x + self.rects[i].ll.x),
									  lly=int(self.pts[prev_pt_idx].y + self.rects[i].ll.y),
									  urx=int(self.pts[prev_pt_idx].x + self.rects[i].ur.x),
									  ury=int(self.pts[prev_pt_idx].y + self.rects[i].ur.y),
									  rect_type=int)
				elif self.pts[prev_pt_idx].x == pt.x:
					# vertical path
					shape = Shape(shape_type=0)
					shape.rect = Rect(llx=int(self.pts[prev_pt_idx].x - self.layer.width * self.design.dbUnits / 2),
									  lly=int(self.pts[prev_pt_idx].y - self.exts[prev_pt_idx]),
									  urx=int(pt.x + self.layer.width * self.design.dbUnits / 2),
									  ury=int(pt.y + self.exts[i]),
									  rect_type=int)
				elif self.pts[prev_pt_idx].y == pt.y:
					# horizontal path
					shape = Shape(shape_type=0)
					shape.rect = Rect(llx=int(self.pts[prev_pt_idx].x - self.exts[prev_pt_idx]),
									  lly=int(self.pts[prev_pt_idx].y - self.layer.width * self.design.dbUnits / 2),
									  urx=int(pt.x + self.exts[i]),
									  ury=int(pt.y + self.layer.width * self.design.dbUnits / 2),
									  rect_type=int)
				else:
					# regular DEF does not allow diagonal shapes, but the following is for VIRTUAL path shape
					shape = Shape(shape_type=2)
					shape.polygon.append(Point(x=int(self.pts[prev_pt_idx].x - self.layer.width * self.design.dbUnits / 2), y=int(self.pts[prev_pt_idx].y - self.layer.width * self.design.dbUnits / 2), point_type=int))
					shape.polygon.append(Point(x=int(pt.x + self.layer.width * self.design.dbUnits / 2), y=int(self.pts[prev_pt_idx].y - self.layer.width * self.design.dbUnits / 2), point_type=int))
					shape.polygon.append(Point(x=int(pt.x + self.layer.width * self.design.dbUnits / 2), y=int(self.pts[prev_pt_idx].y + self.layer.width * self.design.dbUnits / 2), point_type=int))
					shape.polygon.append(Point(x=int(self.pts[prev_pt_idx].x - self.layer.width * self.design.dbUnits / 2), y=int(self.pts[prev_pt_idx].y + self.layer.width * self.design.dbUnits / 2), point_type=int))
				shape.layer = self.layer
				shape['shape_source'] = 'routing'
				shapes.append(shape)
			if not self.isRect[i]:
				prev_pt_idx = i
		return shapes

	def get_via_shapes(self) -> List['Shape']:
		"""
		get shapes of via of this path (represented by vias)

		:return: via shapes of this path
		"""
		shapes = []
		for via in self.vias:
			for via_shape in via.via.botRoutingShapes + via.via.cutShapes + via.via.topRoutingShapes:
				shape = Shape(shape_type=0)
				shape.layer = via_shape.layer
				shape.rect = Rect(llx=int(self.pts[len(self.pts) - 1].x + via_shape.rect.ll.x * self.design.dbUnits),
								  lly=int(self.pts[len(self.pts) - 1].y + via_shape.rect.ll.y * self.design.dbUnits),
								  urx=int(self.pts[len(self.pts) - 1].x + via_shape.rect.ur.x * self.design.dbUnits),
								  ury=int(self.pts[len(self.pts) - 1].y + via_shape.rect.ur.y * self.design.dbUnits),
								  rect_type=int)
				shape['shape_source'] = 'via'
				shape['shape_from'] = via
				shapes.append(shape)
		return shapes

	def change_layer(self, layer_map: Dict[str, str], new_lef: Union['LEF', 'LEFNonDefaultRule']):
		"""
		change LEF layer based on layer_map. the resulting path will point layers in new_lef

		:param layer_map: current layer name:new layer name map
		:param new_lef: LEF object which contains all the new layers
		"""
		self.layer = new_lef.layers[layer_map[self.layer.name]] if self.layer is not None and self.layer.name in layer_map and layer_map[self.layer.name] in new_lef.layers else None

	def is_connected(self, other: Union['DEFPath', List['Shape']]) -> Tuple[bool, List['DEFVia'], Union['LEFLayer', None]]:
		"""
		check whether this path is connected to a path or shapes or not

		:param other: a path or shapes to check connection
		:return: (True if this path and 'other' is connected. if not, False), (via which connects two paths), (layer on which two paths are connected)
		"""
		if 'shapes' not in self:
			self['shapes'] = []
			if len(self.pts) != 0:
				if len(self.pts) > 2:
					logger.warning('there is a path has %d points. currently path with more than 2 points are not supported' % (len(self.pts)))
				elif len(self.pts) == 2 or self.isRect:
					self['shapes'] += self.get_routing_shape()
			if len(self.vias) != 0:
				self['shapes'] += self.get_via_shapes()

		if isinstance(other, DEFPath):
			if 'shapes' not in other:
				other['shapes'] = []
				if len(other.pts) != 0:
					if len(other.pts) > 2:
						logger.warning('there is a path has %d points. currently path with more than 2 points are not supported' % (len(other.pts)))
					elif len(other.pts) == 2 or other.isRect:
						other['shapes'] += other.get_routing_shape()
				if len(other.vias) != 0:
					other['shapes'] += other.get_via_shapes()
			targ_shapes = other['shapes']
		else:
			targ_shapes = other

		for self_shape in self['shapes']:
			for targ_shape in targ_shapes:
				if self_shape.is_intersected(targ_shape):
					connection_vias = []
					if 'shape_source' in self_shape and self_shape['shape_source'] == 'via':
						connection_vias.append(self_shape['shape_from'])
					if 'shape_source' in targ_shape and targ_shape['shape_source'] == 'via':
						connection_vias.append(targ_shape['shape_from'])
					return True, connection_vias, self_shape.layer
		return False, [], None


class DEFWire:
	"""
	represents a wire of nets in the specified design
	"""
	layer: Union['LEFLayer', None]
	'''
	LEF layer that the wire is on
	'''
	paths: List['DEFPath']
	'''
	list of paths consisting the wire
	'''
	type: int
	'''
	type of the wire
	-1: NULL
	0: cover
	1: fixed
	2: routed
	'''
	props: Dict[str, Any]
	'''
	user-defined properties
	'''

	def __init__(self, swig_ref: LEFDEF.DEFWire = None, design: 'DEFDesign' = None):
		"""
		create a wire of nets in the specified design

		:param swig_ref: imported DEFWire from LEFDEF C++ library, if not specified, create empty object
		:param design: DEFDesign which this DEFWire belongs to. DEFDesign should have a valid DEF as member, and the DEF should have a valid LEF as member which has full list of LEF layers
		"""
		if swig_ref is None:
			self.layer = None
			self.paths = []
			self.type = -1
		else:
			if design is not None:
				self.layer = design.DEF.LEF.layers[swig_ref.layer_name] if swig_ref.layer_name in design.DEF.LEF.layers else None
				self.paths = [DEFPath(path, design) for path in list(swig_ref.paths)]
			else:
				self.layer = None
				self.paths = [DEFPath(path) for path in list(swig_ref.paths)]
			self.type = swig_ref.type
		self.props = {}

	def __setitem__(self, key, value):
		self.props[key] = value

	def __getitem__(self, item):
		return self.props[item]

	def __contains__(self, item):
		if item in self.props:
			return True
		else:
			return False

	def export(self) -> LEFDEF.DEFWire:
		"""
		export the wire of nets to LEFDEF C++ library

		:return: DEFWire in LEFDEF C++ library
		"""
		targ = LEFDEF.DEFWire()
		targ.layer_name = self.layer.name if self.layer is not None else ''
		targ.paths = LEFDEF.VecDEFPath([path.export() for path in self.paths])
		targ.type = self.type
		return targ

	def copy(self, design: 'DEFDesign') -> 'DEFWire':
		"""
		copy the object

		:param design: DEFDesign which this DEFWire belongs to. DEFDesign should have a valid DEF as member, and the DEF should have a valid LEF as member which has full list of LEF layers
		:return: copied object
		"""
		cp = DEFWire()
		cp.layer = design.DEF.LEF.layers[self.layer.name] if self.layer is not None and self.layer.name in design.DEF.LEF.layers else None
		cp.paths = [path.copy(design) for path in self.paths]
		cp.type = self.type
		cp.props = self.props.copy()
		return cp

	def change_layer(self, layer_map: Dict[str, str], new_lef: Union['LEF', 'LEFNonDefaultRule']):
		"""
		change LEF layer based on layer_map. the resulting wire will point layers in new_lef

		:param layer_map: current layer name:new layer name map
		:param new_lef: LEF object which contains all the new layers
		"""
		self.layer = new_lef.layers[layer_map[self.layer.name]] if self.layer is not None and self.layer.name in layer_map and layer_map[self.layer.name] in new_lef.layers else None
		for path in self.paths:
			path.change_layer(layer_map, new_lef)


class DEFNetDirectedGraph(directedgraph.DirectedGraph):
	def __init__(self, data: Dict[Union[str, int, float], Set[Union[str, int, float]]] = None, hypergraph: hypergraph.HyperGraph = None):
		if hypergraph is None:
			super().__init__(data)
		else:
			self.nodes = hypergraph.nodes
			self.edges = hypergraph.edges

	def draw(self, dot_filename: str = None, highlight_edge_cutLayers: List[str] = None):
		"""
		draw directed graph for a net (connection among paths, component pins, pins)

		:param dot_filename: name of the dot file (please check graphviz to see what dot files are) (convert dot file into png: dot -Tpng <dot_filename> -o <png_filename> in commandline
		:param highlight_edge_cutLayers:  edges whose connection is based on this cut layer is highlighted in red in the resulting graph
		"""
		import networkx as nx

		G = nx.DiGraph()
		for node_name, node_info in self.nodes.items():
			G.add_node(node_name)
			G.nodes[node_name]['label'] = node_name

			if node_info['type'] == 'pin':
				pin_layers = set()
				for shape in node_info['pin'].shapes:
					pin_layers.add(shape.layer.name)
				G.nodes[node_name]['label'] += '\n' + 'LAYER: ' + ', '.join(list(pin_layers))
			elif node_info['type'] == 'comp_pin':
				pin_layers = set()
				for shape in node_info['comp_pin'].pin.shapes:
					pin_layers.add(shape.layer.name)
				G.nodes[node_name]['label'] += '\n' + 'LAYER: ' + ', '.join(list(pin_layers))
			else:
				G.nodes[node_name]['label'] += '\n' + 'LAYER: ' + node_info['path'].layer.name
				node_path = node_info['path']
				if len(node_path.pts) > 0:
					pts_coordinates_def = []
					pts_coordinates_real = []
					for pt in node_path.pts:
						pts_coordinates_def.append('(%d, %d)' % (pt.x, pt.y))
						pts_coordinates_real.append('(%.3f, %.3f)' % (pt.x / node_path.design.dbUnits, pt.y / node_path.design.dbUnits))
					pts_def_str = ' -> '.join(pts_coordinates_def)
					pts_real_str = ' -> '.join(pts_coordinates_real)
					G.nodes[node_name]['label'] += '\n' + 'PTS(DEF): ' + pts_def_str + '\n' + 'PTS(REAL): ' + pts_real_str

				if len(node_path.vias) > 0:
					via_names = []
					for via in node_path.vias:
						via_names.append(via.via.name)
					via_str = ', '.join(via_names)
					G.nodes[node_name]['label'] += '\n' + 'VIAS: ' + via_str

		for edge_name, edge_info in self.edges.items():
			if edge_info['connected_layer'] is not None:
				edge_label = edge_info['connected_layer'].name
			else:
				edge_label = ''
			edge_options = {}
			connection_via_names = []
			if 'connection_vias' in edge_info and len(edge_info['connection_vias']) > 0:
				for via in edge_info['connection_vias']:
					connection_via_names.append(via.via.name)
					if highlight_edge_cutLayers is not None and via.via.cutLayer.name in highlight_edge_cutLayers:
						edge_options = {'color': 'red', 'penwidth': 3}
				edge_label += '\n' + 'BY VIA: ' + ', '.join(connection_via_names)
			G.add_edge(edge_info['from'], edge_info['to'], label=edge_label, **edge_options)

		nx.nx_agraph.write_dot(G, dot_filename)


class DEFNet:
	"""
	represents a net in the specified design
	"""
	name: str
	'''
	name of the net
	'''
	design: Union['DEFDesign', None]
	'''
	design that this net belongs to
	'''
	source: int
	'''
	source of the net
	0: netlist
	1: dist
	2: timing
	3: user
	4: test
	'''
	type: int
	'''
	type of the net
	0: analog
	1: clock
	2: ground
	3: power
	4: reset
	5: scan
	6: signal
	7: tieoff
	'''
	routingPattern: int
	'''
	routing pattern of the net
	0: balanced
	1: steiner
	2: trunk
	3: wiredlogic
	'''
	pins: List['DEFPin']
	'''
	design pins (ports) connected to this net
	'''
	compPins: List['DEFComponentPin']
	'''
	component pins connected to this net
	'''
	wires: List['DEFWire']
	'''
	wires consisting this net
	'''
	# SNET
	voltage: int
	'''
	for special nets, voltage of this net in mV
	'''
	shape: int
	'''
	for special nets, the shape of this net
	-1: NULL
	0: RING
	1: PADRING
	2: BLOCKRING
	3: STRIPE
	4: FOLLOWPIN
	5: IOWIRE
	6: COREWIRE
	7: BLOCKWIRE
	8: FILLWIRE
	9: BLOCKAGEWIRE
	10: DRCFILL	
	'''
	props: Dict[str, Any]
	'''
	user-defined properties
	'''

	def __init__(self, swig_ref: LEFDEF.DEFNet = None, design: 'DEFDesign' = None, exclude_wires: bool = False, verilog_net = None):
		"""
		create a net in the specified design

		:param swig_ref: imported DEFNet from LEFDEF C++ library, if not specified, create empty object
		:param design: DEFDesign which this DEFNet belongs to. DEFDesign should have pin(port) and component definitions as well as DEF, and the DEF should have a valid LEF as member which has full list of LEF layers and macro definitions
		:param exclude_wires: exclude wire shapes from DEF file. connection information will still remain
		"""
		if swig_ref is None and verilog_net is None:
			self.name = ''
			self.design = None
			self.source = 0
			self.type = 6
			self.routingPattern = 1

			self.pins = []
			self.compPins = []
			self.wires = []

			self.voltage = -1
			self.shape = -1
		elif swig_ref is None and verilog_net is not None:
			verilog_obj = verilog_net[0]
			net_name = verilog_net[1]

			self.name = net_name
			self.design = design
			self.source = 0
			self.type = 6
			self.routingPattern = 1
			self.pins = []
			self.compPins = []
			self.wires = []
			if design is not None:
				for ins_pin in verilog_obj.net_compPin_dict[str(net_name)]:
					if ins_pin.pin in verilog_obj.port_list:
						self.pins.append(design.pins[ins_pin.pin])
					self.compPins.append(DEFComponentPin(design=design, verilog_compPin=ins_pin))
					# else:
					# 	self.compPins.append(DEFComponentPin(design=design, verilog_compPin=ins_pin))
				for component_pin in self.compPins:
					if component_pin.comp.macro not in design.sub_module:
					# if component_pin.comp.name not in design.sub_module:
						component_pin.comp.pin2net[component_pin.pin.name] = self
					else:
						for module_pin in component_pin.pin:
							component_pin.comp.pin2net[module_pin] = self

				for pin in self.pins:
					pin.net = self

			self.voltage = -1
			self.shape = -1
		else:
			self.name = swig_ref.name
			self.design = design
			self.source = swig_ref.source
			self.type = swig_ref.type
			self.routingPattern = swig_ref.routingPattern
			if design is not None:
				self.pins = [design.pins[pin_name] for pin_name in list(swig_ref.pin_names)]
				for pin in self.pins:
					pin.net = self
				self.compPins = [DEFComponentPin(swig_ref=comp_pin, design=design) for comp_pin in list(swig_ref.component_pin_names)]
				for component_pin in self.compPins:
					component_pin.comp.pin2net[component_pin.pin.name] = self
				if not exclude_wires:
					self.wires = [DEFWire(wire, design) for wire in list(swig_ref.wires)]
				else:
					self.wires = []
			else:
				self.pins = []
				self.compPins = []
				if not exclude_wires:
					self.wires = [DEFWire(wire) for wire in list(swig_ref.wires)]
				else:
					self.wires = []
			self.voltage = swig_ref.voltage
			self.shape = swig_ref.shape
		self.props = {}

	def __setitem__(self, key, value):
		self.props[key] = value

	def __getitem__(self, item):
		return self.props[item]

	def __contains__(self, item):
		if item in self.props:
			return True
		else:
			return False

	def export(self) -> LEFDEF.DEFNet:
		"""
		export the net to LEFDEF C++ library

		:return: DEFNet in LEFDEF C++ library
		"""
		targ = LEFDEF.DEFNet()
		targ.name = self.name
		targ.source = self.source
		targ.type = self.type
		targ.routingPattern = self.routingPattern

		targ.pin_names = LEFDEF.VecStr([pin.name for pin in self.pins])
		targ.component_pin_names = LEFDEF.VecDEFCompPin([comp_pin.export() for comp_pin in self.compPins])
		targ.wires = LEFDEF.VecDEFWire([wire.export() for wire in self.wires])

		targ.voltage = self.voltage
		targ.shape = self.shape
		return targ

	def copy(self, design: 'DEFDesign', exclude_wires: bool = False) -> 'DEFNet':
		"""
		copy the object

		:param design: DEFDesign which this DEFNet belongs to. DEFDesign should have pin(port) and component definitions as well as DEF, and the DEF should have a valid LEF as member which has full list of LEF layers and macro definitions
		:param exclude_wires: exclude wire shapes from copying. connection information will still remain
		:return: copied object
		"""
		cp = DEFNet()
		cp.name = self.name
		cp.design = design
		cp.source = self.source
		cp.type = self.type
		cp.routingPattern = self.routingPattern

		cp.pins = []
		for pin in self.pins:
			if pin.name in design.pins:
				cp.pins.append(design.pins[pin.name])
		for pin in cp.pins:
			pin.net = cp
		cp.compPins = [comp_pin.copy(design) for comp_pin in self.compPins]
		for comp_pin in cp.compPins:
			comp_pin.comp.pin2net[comp_pin.pin.name] = cp
		if not exclude_wires:
			cp.wires = [wire.copy(design) for wire in self.wires]

		cp.voltage = self.voltage
		cp.shape = self.shape
		cp.props = self.props.copy()
		return cp

	def copy_only_header(self, design: 'DEFDesign') -> 'DEFNet':
		"""
		copy only header of net (connected pins, compPins, wires will be excluded for copying)

		:return: copied object
		"""
		cp = DEFNet()
		cp.name = self.name
		cp.design = design
		cp.source = self.source
		cp.type = self.type
		cp.routingPattern = self.routingPattern

		cp.voltage = self.voltage
		cp.shape = self.shape
		cp.props = self.props.copy()
		return cp

	def change_layer(self, layer_map: Dict[str, str], new_lef: Union['LEF', 'LEFNonDefaultRule']):
		"""
		change LEF layer based on layer_map. the resulting net will point layers in new_lef

		:param layer_map: current layer name:new layer name map
		:param new_lef: LEF object which contains all the new layers
		"""
		for wire in self.wires:
			wire.change_layer(layer_map, new_lef)

	def get_existing_cutLayers(self, cutLayer_names: List[str]) -> List[str]:
		"""
		check whether paths in this net contains vias with the specified cut layers

		:param cutLayer_names: cut layer name to check
		:return: list of cut layer names which exist in the paths of this net
		"""
		existing_cutLayer_names = []
		for wire in self.wires:
			for path in wire.paths:
				for via in path.vias:
					if via.via.cutLayer.name in cutLayer_names:
						existing_cutLayer_names.append(via.via.cutLayer.name)
					if len(existing_cutLayer_names) == len(cutLayer_names):
						break
				if len(existing_cutLayer_names) == len(cutLayer_names):
					break
			if len(existing_cutLayer_names) == len(cutLayer_names):
				break
		return existing_cutLayer_names

	def build_edges_directedgraph(self, DG: DEFNetDirectedGraph, cur_node_name: str, bfs_queue: List[str]):
		"""
		build edges between nodes which connected with current node

		:param DG: directed graph to traverse
		:param cur_node_name: current node name
		:param bfs_queue: nodes to perform tracing
		"""
		DG.nodes[cur_node_name]['visited'] = True
		cur_node_info = DG.nodes[cur_node_name]

		for targ_node_name, targ_node_info in DG.nodes.items():
			if cur_node_name != targ_node_name and cur_node_name not in targ_node_info['nodes_already_checked_connection']:

				if cur_node_info['type'] == 'path':
					cur_node_path = cur_node_info['path']
					layer_order = cur_node_path.design.DEF.LEF.layer_order
					if targ_node_info['type'] == 'path':
						targ_node_path = targ_node_info['path']
						connected, connection_vias, connected_layer = cur_node_path.is_connected(targ_node_path)
						if connected:
							cur_node_path_layer_idx = layer_order.index(cur_node_path.layer)
							targ_node_path_layer_idx = layer_order.index(targ_node_path.layer)
						else:
							cur_node_path_layer_idx = None
							targ_node_path_layer_idx = None
					else:
						targ_node_shapes = targ_node_info['shapes']
						connected, connection_vias, connected_layer = cur_node_path.is_connected(targ_node_shapes)
						if connected:
							cur_node_path_layer_idx = layer_order.index(cur_node_path.layer)
							targ_node_path_layer_idx = layer_order.index(connected_layer)
						else:
							cur_node_path_layer_idx = None
							targ_node_path_layer_idx = None
				else:
					cur_node_shapes = cur_node_info['shapes']
					if targ_node_info['type'] == 'path':
						targ_node_path = targ_node_info['path']
						layer_order = targ_node_path.design.DEF.LEF.layer_order
						connected, connection_vias, connected_layer = targ_node_path.is_connected(cur_node_shapes)
						if connected:
							cur_node_path_layer_idx = layer_order.index(connected_layer)
							targ_node_path_layer_idx = layer_order.index(targ_node_path.layer)
						else:
							cur_node_path_layer_idx = None
							targ_node_path_layer_idx = None
					else:
						# we know one of cur_node or targ_node should be path (not pin nor comp_pin)
						# because a pin cannot be directly connected to comp_pin or other pin
						# (pin and comp_pin should be connected to a path)
						layer_order = []
						connected = False
						connection_vias = []
						connected_layer = None
						cur_node_path_layer_idx = None
						targ_node_path_layer_idx = None

				# all connection via should be between two path layers,
				for connection_via in connection_vias[:]:
					topRoutingLayer_idx = max(cur_node_path_layer_idx, targ_node_path_layer_idx)
					botRoutingLayer_idx = min(cur_node_path_layer_idx, targ_node_path_layer_idx)
					connection_via_topRoutingLayer_idx = layer_order.index(connection_via.via.topRoutingLayer)
					connection_via_botRoutingLayer_idx = layer_order.index(connection_via.via.botRoutingLayer)
					if not (topRoutingLayer_idx >= connection_via_topRoutingLayer_idx  and connection_via_botRoutingLayer_idx >= botRoutingLayer_idx):
						connection_vias.remove(connection_via)

				if connected:
					if targ_node_name not in DG.predecessors(cur_node_name):
						if 'in_edges' in targ_node_info and len(targ_node_info['in_edges']) > 0:
							'''
							if target node already has an incoming edge, replace it with an edge from the current node because it will be the longer path
							cur_path is node E, targ_path is node C
							node A -----> node B ------------> node C -----> node D 
							                 |                   ^
							         edge 1  |-----> node E -----|  edge 2
							===>
							node A -----> node B               node C -----> node D 
							                 |                   ^
							         edge 1  |-----> node E -----|  edge 2
							
							however, a corner case would be 
							1.
							if edge 1 and edge 2 are using the same via, it should be something like this
							node A -----> node B ------------> node C -----> node D 
							                 |                   ^
							         edge 1  |-----> node E -----|  edge 2
							===>
							node A -----> node B ------------> node C -----> node D 
							                 |
							         edge 1  |-----> node E 
							
							2.
							the vias in the shorter path includes all the vias in the longer path
							                        edge 3 (via z, via y)
							node A -----> node B ------------> node C -----> node D 
							                 |                   ^
							         edge 1  |-----> node E -----|  edge 2
							        (via z)                         (via y)
							===>
							node A -----> node B               node C -----> node D 
							                 |                   ^
							         edge 1  |-----> node E -----|  edge 2
							
							3.
							the via in the shorter path is included to the last paths of the longer path
							                        edge 3 (via z)
							node A -----> node B ------------> node C -----> node D 
							                 |                   ^
							         edge 1  |-----> node E -----|  edge 2
							        (via y)                         (via z, y)
							===>
							node A -----> node B ------------> node C -----> node D 
							                 |
							         edge 1  |-----> node E 
							
							4.
							the via in the shorter path is included to the first paths of the longer path
							                        edge 3 (via z)
							node A -----> node B ------------> node C -----> node D 
							                 |                   ^
							         edge 1  |-----> node E -----|  edge 2
							        (via z, y)                      (via y)
							===>
							node A -----> node B ------------> node C -----> node D 
							                                     |
							                         node E <----|  edge 2
							5.
							if a via as used in the first path of the longer path, it cannot be used again 
							                        edge 3 (any)
							node A -----> node B ------------> node C -----> node D 
							                 |                   ^
							         edge 1  |-----> node E -----|  edge 2
							        (via z, y)                      (via x, y)
							===>
							node A -----> node B ------------> node C -----> node D 
							                                     |
							                         node E <----|  edge 2
							'''
							#as we are using BFS, if a node examined first (get included in in_edges), it will become cur_node first. So, index [0] would be fine.
							if len(connection_vias) > 0 and len(cur_node_info['in_edges'][0]['connection_vias']) > 0 and set(connection_vias) == set(cur_node_info['in_edges'][0]['connection_vias']):
								# corner case 1
								pass
							elif len(connection_vias) > 0 \
									and len(connection_vias) == len(cur_node_info['in_edges'][0]['connection_vias']) + len(targ_node_info['in_edges'][0]['connection_vias']) \
									and set(cur_node_info['in_edges'][0]['connection_vias']).issubset(set(connection_vias)) and set(targ_node_info['in_edges'][0]['connection_vias']).issubset(set(connection_vias)):
								# corner case 3
								pass
							elif len(cur_node_info['in_edges'][0]['connection_vias']) > 0 \
									and len(connection_vias) + len(targ_node_info['in_edges'][0]['connection_vias']) == len(cur_node_info['in_edges'][0]['connection_vias']) \
									and set(connection_vias).issubset(set(cur_node_info['in_edges'][0]['connection_vias'])) and set(targ_node_info['in_edges'][0]['connection_vias']).issubset(set(cur_node_info['in_edges'][0]['connection_vias'])):
								# corner case 4
								DG.remove_edge(cur_node_info['in_edges'][0].name)
								DG.add_edge('%s_%s' % (targ_node_name, cur_node_name), [targ_node_name, cur_node_name], connection_vias=connection_vias, connected_layer=connected_layer)
							else:
								if set(connection_vias).intersection(set(cur_node_info['in_edges'][0]['connection_vias'])):
									# corner case 5
									pass
								else:
									DG.remove_edge(targ_node_info['in_edges'][0].name)
									DG.add_edge('%s_%s' % (cur_node_name, targ_node_name), [cur_node_name, targ_node_name], connection_vias=connection_vias, connected_layer=connected_layer)
						else:
							DG.add_edge('%s_%s' % (cur_node_name, targ_node_name), [cur_node_name, targ_node_name], connection_vias=connection_vias, connected_layer=connected_layer)

					if not targ_node_info['visited'] and targ_node_name not in bfs_queue:
						bfs_queue.insert(0, targ_node_name)

				DG.nodes[cur_node_name]['nodes_already_checked_connection'].append(targ_node_name)
				DG.nodes[targ_node_name]['nodes_already_checked_connection'].append(cur_node_name)

	def get_net_directedgraph(self, row_splitting: bool = False, macro_map_3d_to_2d: Dict[str, Tuple[int, str]] = None) -> DEFNetDirectedGraph:
		"""
		generate a directed graph with nodes representing path, and edges representing connection among paths

		:param row_splitting: when 3D DEF, whether the design is using half height macros (used in compact2D)
		:param macro_map_3d_to_2d: when 3D DEF and row_splitting enabled, 3D macro name:(tier_num, 2D macro name)
		:return: directed graph showing the connection of paths in this net
		"""
		DG = DEFNetDirectedGraph()

		driver_node = None
		for pin in self.pins:
			if 'shapes' not in pin:
				pin['shapes'] = pin.get_pin_shapes_in_design()
			pin_node_name = 'PIN_%s' % (pin.name)
			DG.add_node(pin_node_name, type='pin', pin=pin, shapes=pin['shapes'], visited=False, root=False, nodes_already_checked_connection=[])
			if pin.direction == 0:
				driver_node = DG.nodes[pin_node_name]
				driver_node.root = True

		for comp_pin in self.compPins:
			if 'shapes' not in comp_pin:
				comp_pin['shapes'] = comp_pin.get_comp_pin_shapes_in_design()
				if row_splitting and macro_map_3d_to_2d is not None:
					tier_num = macro_map_3d_to_2d[comp_pin.comp.macro.name][0]
					if comp_pin.comp.is_shifted_by_row_splitting(tier_num):
						for shape in comp_pin['shapes']:
							shape.move(0, int(comp_pin.comp.macro.origin.y * self.design.dbUnits))
			comp_pin_node_name = 'COMP_PIN_%s/%s' % (comp_pin.comp.name, comp_pin.pin.name)
			DG.add_node(comp_pin_node_name, type='comp_pin', comp_pin=comp_pin, shapes=comp_pin['shapes'], visited=False, root=False, nodes_already_checked_connection=[])
			if comp_pin.pin.direction == 1:
				driver_node = DG.nodes[comp_pin_node_name]
				driver_node.root = True

		for wire_num, wire_info in enumerate(self.wires):
			for path_num, path_info in enumerate(wire_info.paths):
				DG.add_node('%s_W%dP%d' % (self.name, wire_num, path_num), type='path', wire=wire_info, path=path_info, visited=False, root=False, nodes_already_checked_connection=[])

		if driver_node is not None:
			# need to perform BFS instead of DFS since a signal is propagated from the root.
			# if we perform DFS, it can be end up with a loop
			bfs_queue = [driver_node.name]
			while len(bfs_queue) > 0:
				cur_node_name = bfs_queue.pop()
				self.build_edges_directedgraph(DG, cur_node_name, bfs_queue)
		else:
			logger.error('cannot identify the driver for net %s. ignored' % self.name)

		return DG

	def split_by_cutLayer(self, cutLayer_name: str, row_splitting: bool = False, macro_map_3d_to_2d: Dict[str, Tuple[int, str]] = None) -> List[str]:
		"""
		split a net into multiple nets by cutting nets on a cut layer (cutLayer_name)

		:param cutLayer_name: cut layer which will split nets on
		:param row_splitting: when 3D DEF, whether the design is using half height macros (used in compact2D)
		:param macro_map_3d_to_2d: when 3D DEF and row_splitting enabled, 3D macro name:(tier_num, 2D macro name)
		:return: names of the split nets (subnets)
		"""
		DG = self.get_net_directedgraph(row_splitting, macro_map_3d_to_2d)
		num_vias_target_cutLayer = 0
		for node_name, node_info in DG.nodes.items():
			if node_info['type'] == 'path':
				for via in node_info['path'].vias:
					if via.via.cutLayer.name == cutLayer_name:
						num_vias_target_cutLayer += 1

		subnet_num = 0
		for edge_name in list(DG.edges.keys()):
			edge_info = DG.edges[edge_name]
			for connection_via in edge_info['connection_vias']:
				if connection_via.via.cutLayer.name == cutLayer_name:
					# 'from' and 'to' attributes are automatically set by DirectedGraph
					# 'from' and 'to' node paths are connected by ILV (connection_via) at connected_layer
					connected_layer = edge_info['connected_layer']
					pin_layers = {}
					if DG.nodes[edge_info['from']]['type'] == 'path' and connection_via in DG.nodes[edge_info['from']]['path'].vias:
						# this means ILV is in driver path
						# that means connected_layer is at receiver path
						pin_layers['to_pin'] = connected_layer
						if pin_layers['to_pin'].name == connection_via.via.botRoutingLayer.name:
							pin_layers['from_pin'] = connection_via.via.topRoutingLayer
						else:
							pin_layers['from_pin'] = connection_via.via.botRoutingLayer
					else:
						# this means ILV is in receiver path
						# that means connected_layer is at driver path
						pin_layers['from_pin'] = connected_layer
						if pin_layers['from_pin'].name == connection_via.via.botRoutingLayer.name:
							pin_layers['to_pin'] = connection_via.via.topRoutingLayer
						else:
							pin_layers['to_pin'] = connection_via.via.botRoutingLayer

					for direction in ['from', 'to']:
						pin_layer = pin_layers[direction + '_pin']
						subnet_name = self.name + '_' + str(subnet_num)
						# make ILV pins
						ilv_pin = DEFPin()
						if direction == 'from':
							ilv_pin.name = 'ILV_OUT_' + subnet_name
							ilv_pin.direction = 1
						else:
							ilv_pin.name = 'ILV_IN_' + subnet_name
							ilv_pin.direction = 0
						ilv_pin['parent_net_name'] = 'ILV_' + subnet_name
						ilv_pin.design = self.design
						ilv_pin.net = self
						if pin_layer.name == connection_via.via.botRoutingLayer.name:
							for shape in connection_via.via.botRoutingShapes:
								ilv_pin_shape = shape.copy(self.design.DEF.LEF.layers)
								ilv_pin_shape.scale(scale_factor=self.design.dbUnits)
								ilv_pin_shape.to_integer()
								ilv_pin.shapes.append(ilv_pin_shape)
							#ilv_pin.shapes = [shape.copy(self.design.DEF.LEF.layers).scale(scale_factor=self.design.dbUnits).to_integer() for shape in connection_via.via.botRoutingShapes]
						elif pin_layer.name == connection_via.via.topRoutingLayer.name:
							for shape in connection_via.via.topRoutingShapes:
								ilv_pin_shape = shape.copy(self.design.DEF.LEF.layers)
								ilv_pin_shape.scale(scale_factor=self.design.dbUnits)
								ilv_pin_shape.to_integer()
								ilv_pin.shapes.append(ilv_pin_shape)
							#ilv_pin.shapes = [shape.copy(self.design.DEF.LEF.layers).scale(scale_factor=self.design.dbUnits).to_integer() for shape in connection_via.via.topRoutingShapes]
						else:
							ilv_pin.shapes = []
						ilv_pin.pStatus = 1
						ilv_pin.loc = connection_via.loc.copy()
						ilv_pin.orientation = 0
						self.design.pins[ilv_pin.name] = ilv_pin

						pin_node_name = 'PIN_%s' % ilv_pin.name
						if direction == 'from':
							DG.add_node(pin_node_name, type='pin', pin=ilv_pin, shapes=[], visited=True, root=False, nodes_already_checked_connection=[])
							DG.add_edge('%s_%s' % (edge_info['from'], pin_node_name), [edge_info['from'], pin_node_name], connection_vias=[], connected_layer=None)
						else:
							DG.add_node(pin_node_name, type='pin', pin=ilv_pin, shapes=[], visited=True, root=True, nodes_already_checked_connection=[])
							DG.add_edge('%s_%s' % (pin_node_name, edge_info['to']), [pin_node_name, edge_info['to']], connection_vias=[], connected_layer=None)

						# remove ILV via from driver or receiver path
						if 'path' in DG.nodes[edge_info[direction]] and connection_via in DG.nodes[edge_info[direction]]['path'].vias:
							DG.nodes[edge_info[direction]]['path'].vias.remove(connection_via)

					subnet_num += 1
					# remove connection due to ILV via in DirectedGraph
					DG.remove_edge(edge_name)

		SGs = DG.independent_subgraph()

		if len(SGs) != num_vias_target_cutLayer+1:
			logger.warning('net %s has %d vias with cutLayer %s, but the number of its subnets is %d' % (self.name, num_vias_target_cutLayer, cutLayer_name, len(SGs)))
			DG_original = self.get_net_directedgraph(row_splitting, macro_map_3d_to_2d)
			DG_original.draw(dot_filename=self.name + '.dot', highlight_edge_cutLayers=['ILV_T01'])
			DG.draw(dot_filename=self.name + '.split.dot', highlight_edge_cutLayers=['ILV_T01'])

		subnet_names = []
		for i, SG in enumerate(SGs):
			subnet = DEFNet()
			subnet.name = self.name + '_SUBNET' + str(i)
			subnet.design = self.design

			subnet_wire = DEFWire()
			subnet_wire.type = 2
			for node_name, node_info in SG.nodes.items():
				if node_info['type'] == 'pin':
					subnet.pins.append(node_info['pin'])
				elif node_info['type'] == 'comp_pin':
					subnet.compPins.append(node_info['comp_pin'])
				else:
					subnet_wire.paths.append(node_info['path'])
			subnet.wires.append(subnet_wire)
			for pin in subnet.pins:
				pin.net = subnet
			for comp_pin in subnet.compPins:
				comp_pin.comp.pin2net[comp_pin.pin.name] = subnet
			self.design.nets[subnet.name] = subnet
			subnet_names.append(subnet.name)
		return subnet_names


class DEFDesign:
	"""
	represent a design
	"""
	DEF: Union['DEF', None]
	'''
	DEF which this design belongs to
	'''
	name: str
	'''
	name of the design
	'''
	dbUnits: float
	'''
	DB units of the design
	'''
	defProps: List['DEFProp']
	'''
	list of DEF properties
	'''
	dieArea: Union['Shape', None]
	'''
	die area of the design
	'''
	rows: Dict[str, 'DEFRow']
	'''
	rows in the design
	'''
	tracks: List['DEFTrack']
	'''
	tracks in the design
	'''
	gCellGrids: List['DEFGCellGrid']
	'''
	GCellGrid in the design
	'''
	vias: Dict[str, 'LEFVia']
	'''
	via defined in this design (this is different from via instance in nets)
	'''
	viarules: Dict[str, 'DEFViaRule']
	'''
	via rules defiend in this design
	'''
	components: Dict[str, 'DEFComponent']
	'''
	components in the design
	'''
	pins: Dict[str, 'DEFPin']
	'''
	pins(ports) of the design
	'''
	blockages: List['DEFBlkg']
	'''
	blockages in the design
	'''
	sNets: Dict[str, 'DEFNet']
	'''
	special nets in the design
	'''
	nets: Dict[str, 'DEFNet']
	'''
	nets in the design
	'''
	histories: List[str]
	'''
	list of the history
	'''
	technology: str
	'''
	technology used in the design
	'''
	props: Dict[str, Any]
	'''
	user-defined properties
	'''

	def __init__(self, swig_ref: LEFDEF.DEFDesign = None, DEF: 'DEF' = None, exclude_wires: bool = False, verilog_ref = None):
		"""
		create a design in DEF

		:param swig_ref: imported DEFDesign from LEFDEF C++ library, if not specified, create empty object
		:param DEF: DEF which this design belongs to
		:param exclude_wires: exclude wire shapes from DEF file. connection information will still remain
		"""
		if swig_ref is None and verilog_ref is None:
			self.DEF = None
			self.name = ''
			self.dbUnits = 1000
			self.defProps = []
			self.dieArea = None
			self.rows = {}
			self.tracks = []
			self.gCellGrids = []
			self.vias = {}
			self.viarules = {}
			self.components = {}
			self.pins = {}
			self.blockages = []
			self.sNets = {}
			self.nets = {}
			self.histories = []
			self.technology = ''
		elif swig_ref is None and DEF is not None and verilog_ref is not None:
			self.verilog_module = verilog_ref[0]
			self.sub_module = verilog_ref[1]

			self.DEF = DEF
			self.name = self.verilog_module.module_name
			self.dbUnits = 1000
			self.defProps = []
			self.dieArea = None
			self.rows = {}
			self.tracks = []
			self.gCellGrids = []
			self.vias = {}
			self.viarules = {}
			self.components = {instance.instance_name: DEFComponent(design=self, verilog_comp=instance) for instance in self.verilog_module.module_instances}
			self.pins = {pin_name: DEFPin(design=self, verilog_pins=(verilog_ref, pin_name)) for pin_name in self.verilog_module.port_list}
			self.blockages = []
			self.sNets = {}
			self.module_hier = []
			DEF.hierarchy[self.name] = self.module_hier
			io_net = []
			for net_de in self.verilog_module.net_declarations:
				io_net = io_net + net_de.net_name
			# io_net = verilog_ref.net_declarations[0].net_name + verilog_ref.port_list
			io_net = io_net + self.verilog_module.port_list
			# self.nets = {net_name: DEFNet(design=self, verilog_net=(verilog_ref, net_name)) for net_name in verilog_ref.net_declarations[0].net_name}
			self.nets = {net_name: DEFNet(design=self, verilog_net=(self.verilog_module, net_name)) for net_name in io_net}
			self.histories = []
			self.technology = ''
		else:
			self.DEF = DEF
			self.name = swig_ref.name
			self.dbUnits = swig_ref.dbUnits
			self.defProps = [DEFProp(prop) for prop in list(swig_ref.props)]
			if DEF is not None:
				self.dieArea = Shape(swig_ref=swig_ref.dieArea, layers=self.DEF.LEF.layers)
			else:
				self.dieArea = Shape(swig_ref=swig_ref.dieArea)
			self.rows = {row_name: DEFRow(swig_ref=row_info, design=self) for row_name, row_info in dict(swig_ref.rows).items()}
			self.tracks = [DEFTrack(swig_ref=track, design=self) for track in list(swig_ref.tracks)]
			self.gCellGrids = [DEFGCellGrid(swig_ref=gcg) for gcg in list(swig_ref.gCellGrids)]
			if DEF is not None:
				self.vias = {via_name: LEFVia(swig_ref=via, lef=self.DEF.LEF) for via_name, via in dict(swig_ref.vias).items()}
			else:
				self.vias = {via_name: LEFVia(swig_ref=via) for via_name, via in dict(swig_ref.vias).items()}
			self.viarules = {viarule_name: DEFViaRule(swig_ref=viarule_info, design=self) for viarule_name, viarule_info in dict(swig_ref.viarules).items()}
			self.components = {comp_name: DEFComponent(swig_ref=comp_info, design=self) for comp_name, comp_info in dict(swig_ref.components).items()}
			self.pins = {pin_name: DEFPin(swig_ref=pin_info, design=self) for pin_name, pin_info in dict(swig_ref.pins).items()}
			self.blockages = [DEFBlkg(swig_ref=blkg, design=self) for blkg in list(swig_ref.blockages)]
			self.sNets = {snet_name: DEFNet(swig_ref=snet_info, design=self, exclude_wires=exclude_wires) for snet_name, snet_info in dict(swig_ref.sNets).items()}
			self.nets = {net_name: DEFNet(swig_ref=net_info, design=self, exclude_wires=exclude_wires) for net_name, net_info in dict(swig_ref.nets).items()}
			# normally most of connection between pin and net can be covered by net init function only, but for special nets, they do not explicitly covers connection between pins and special nets, and their connections are covered in pins section only
			self.connect_pin_net()
			self.histories = list(swig_ref.histories)
			self.technology = swig_ref.technology
		self.props = {}

	def __setitem__(self, key, value):
		self.props[key] = value

	def __getitem__(self, item):
		return self.props[item]

	def __contains__(self, item):
		if item in self.props:
			return True
		else:
			return False

	def export(self, DEF: LEFDEF.DEF, floorplan_only: bool = False) -> LEFDEF.DEFDesign:
		"""
		export the design to LEFDEF C++ library

		:param DEF: DEF object that this design belongs to
		:param floorplan_only: the generate def contains only floorplan (no component, no nets, no special net, no pins, no blockage)
		:return: DEFDesign in LEFDEF C++ library
		"""
		logger.info('convert DEF to C structure for SWIG DEF')
		targ = LEFDEF.DEFDesign()
		targ.pDEF = DEF
		targ.name = self.name
		targ.dbUnits = self.dbUnits
		targ.props = LEFDEF.VecDEFProp([prop.export() for prop in self.defProps])
		targ.dieArea = self.dieArea.export() if self.dieArea is not None else LEFDEF.Shape()
		targ.rows = LEFDEF.MapStrDEFRow({row_name: row_info.export() for row_name, row_info in self.rows.items()})
		targ.tracks = LEFDEF.VecDEFTrack([track.export() for track in self.tracks])
		targ.gCellGrids = LEFDEF.VecDEFGCG([gcellgrid.export() for gcellgrid in self.gCellGrids])
		targ.vias = LEFDEF.MapStrLEFVia({via_name: via_info.export() for via_name, via_info in self.vias.items()})
		targ.viarules = LEFDEF.MapStrDEFViaRule({viarule_name: viarule_info.export() for viarule_name, viarule_info in self.viarules.items()})
		if not floorplan_only:
			targ.components = LEFDEF.MapStrDEFComp({comp_name: comp_info.export() for comp_name, comp_info in self.components.items()})
			targ.pins = LEFDEF.MapStrDEFPin({pin_name: pin_info.export() for pin_name, pin_info in self.pins.items()})
			targ.blockages = LEFDEF.VecDEFBlkg([blockage.export() for blockage in self.blockages])
			targ.sNets = LEFDEF.MapStrDEFNet({snet_name: snet_info.export() for snet_name, snet_info in self.sNets.items()})
			targ.nets = LEFDEF.MapStrDEFNet({net_name: net_info.export() for net_name, net_info in self.nets.items()})
		targ.histories = LEFDEF.VecStr(self.histories)
		targ.technology = self.technology
		return targ

	def copy(self, DEF: 'DEF', exclude_wires: bool = False) -> 'DEFDesign':
		"""
		copy the object

		:param DEF: DEF object that this design belongs to
		:param exclude_wires: exclude wire shapes from copying. connection information will still remain
		:return: copied object
		"""
		logger.info('copying DEF design %s' % self.name)
		cp = DEFDesign()
		cp.DEF = DEF
		cp.name = self.name
		cp.dbUnits = self.dbUnits
		cp.defProps = [prop.copy() for prop in self.defProps]
		cp.dieArea = self.dieArea.copy(DEF.LEF.layers) if self.dieArea is not None else None
		cp.rows = {row_name: row_info.copy(cp) for row_name, row_info in self.rows.items()}
		cp.tracks = [track.copy(cp) for track in self.tracks]
		cp.gCellGrids = [gcellgrid.copy() for gcellgrid in self.gCellGrids]
		cp.vias = {via_name: via_info.copy(DEF.LEF) for via_name, via_info in self.vias.items()}
		cp.viarules = {viarule_name: viarule_info.copy(cp) for viarule_name, viarule_info in self.viarules.items()}
		cp.components = {comp_name: comp_info.copy(cp) for comp_name, comp_info in self.components.items()}
		cp.pins = {pin_name: pin_info.copy(cp) for pin_name, pin_info in self.pins.items()}
		cp.blockages = [blockage.copy(cp) for blockage in self.blockages]
		cp.sNets = {snet_name: snet_info.copy(cp) for snet_name, snet_info in self.sNets.items()}
		cp.nets = {net_name: net_info.copy(cp, exclude_wires) for net_name, net_info in self.nets.items()}
		cp.connect_pin_net()
		cp.histories = self.histories[:]
		cp.technology = self.technology
		cp.props = self.props.copy()
		return cp

	def copy_only_header(self, DEF: 'DEF'):
		"""
		copy only header of design (components, pins, blockages, sNets, nets will be excluded for copying)

		:return: copied object
		"""
		cp = DEFDesign()
		cp.DEF = DEF
		cp.name = self.name
		cp.dbUnits = self.dbUnits
		cp.defProps = [prop.copy() for prop in self.defProps]
		cp.dieArea = self.dieArea.copy(DEF.LEF.layers) if self.dieArea is not None else None
		cp.rows = {row_name: row_info.copy(cp) for row_name, row_info in self.rows.items()}
		cp.tracks = [track.copy(cp) for track in self.tracks]
		cp.gCellGrids = [gcellgrid.copy() for gcellgrid in self.gCellGrids]
		cp.vias = {via_name: via_info.copy(DEF.LEF) for via_name, via_info in self.vias.items()}
		cp.viarules = {viarule_name: viarule_info.copy(cp) for viarule_name, viarule_info in self.viarules.items()}

		cp.histories = self.histories[:]
		cp.technology = self.technology
		cp.props = self.props.copy()
		return cp

	def connect_pin_net(self):
		"""
		normally most of connection between pin and net can be covered by net init function only,
		but for special nets, they do not explicitly covers connection between pins and special nets,
		and their connections are covered in pins section only
		"""
		for pin_name, pin_info in self.pins.items():
			if pin_info.net is None:
				if pin_info.net_name in self.sNets:
					pin_info.net = self.sNets[pin_info.net_name]
					if pin_info not in pin_info.net.pins:
						pin_info.net.pins.append(pin_info)
				elif pin_info.net_name in self.nets:
					pin_info.net = self.nets[pin_info.net_name]
					if pin_info not in pin_info.net.pins:
						pin_info.net.pins.append(pin_info)
				else:
					logger.warning('design pin %s is not connnected any of the regular/special nets. cannot find net \'%s\' in this design' % (pin_name, pin_info.net_name))

	def write_def(self, def_file: str, floorplan_only: bool = False):
		"""
		write the design to DEF file

		:param def_file: filename to write
		:param floorplan_only: the generate def contains only floorplan (no component, no nets, no special net, no pins, no blockage)
		"""
		logger.info('start writing DEF file %s' % def_file)
		swigDEF = self.DEF.export(self.name, floorplan_only)
		logger.info('run LEFDEF SWIG to write %s' % def_file)
		swigDEF.write_def(def_file, self.name)
		logger.info('writing %s done' % def_file)

	def write_verilog(self, verilog_file: str):
		"""
		write verilog file of the specified design

		:param verilog_file: filename to write
		"""

		# group top-level IO port bits into bus port
		grouped_pins = {}
		pin_names_excl_pwr_gnd = list(filter(lambda pin_name: self.pins[pin_name].type != 2 and self.pins[pin_name].type != 3, self.pins.keys()))
		for pin_num, pin_name in enumerate(pin_names_excl_pwr_gnd):
			if self.pins[pin_name].type != 2 and self.pins[pin_name].type != 3:
				match = re.match(r'(?P<bus_name>\S+)'+re.escape(self.DEF.busBitChars[0])+r'(?P<bus_bit>\d+)'+re.escape(self.DEF.busBitChars[1]), pin_name)
				if match is not None:
					bus_name = match['bus_name']
					bus_bit = int(match['bus_bit'])
					if bus_name in grouped_pins:
						if grouped_pins[bus_name]['max_bit'] < bus_bit:
							grouped_pins[bus_name]['max_bit'] = bus_bit
						if grouped_pins[bus_name]['min_bit'] > bus_bit:
							grouped_pins[bus_name]['min_bit'] = bus_bit
					else:
						grouped_pins[bus_name] = {}
						grouped_pins[bus_name]['is_bus'] = True
						grouped_pins[bus_name]['direction'] = self.pins[pin_name].direction
						grouped_pins[bus_name]['max_bit'] = bus_bit
						grouped_pins[bus_name]['min_bit'] = bus_bit
				else:
					grouped_pins[pin_name] = {}
					grouped_pins[pin_name]['is_bus'] = False
					grouped_pins[pin_name]['direction'] = self.pins[pin_name].direction

		# group top-level wire bits into bus wire
		grouped_nets = {}
		for net_name, net_info in self.nets.items():
			if net_info.type != 2 and net_info.type != 3:
				match = re.match(r'(?P<bus_name>\S+)'+re.escape(self.DEF.busBitChars[0])+r'(?P<bus_bit>\d+)'+re.escape(self.DEF.busBitChars[1]), net_name)
				if match is not None:
					bus_name = match['bus_name']
					bus_bit = int(match['bus_bit'])
					if bus_name in grouped_nets:
						if grouped_nets[bus_name]['max_bit'] < bus_bit:
							grouped_nets[bus_name]['max_bit'] = bus_bit
						if grouped_nets[bus_name]['min_bit'] > bus_bit:
							grouped_nets[bus_name]['min_bit'] = bus_bit
					else:
						grouped_nets[bus_name] = {}
						grouped_nets[bus_name]['is_bus'] = True
						grouped_nets[bus_name]['max_bit'] = bus_bit
						grouped_nets[bus_name]['min_bit'] = bus_bit
				else:
					grouped_nets[net_name] = {}
					grouped_nets[net_name]['is_bus'] = False

		logger.info('start writing verilog file %s' % verilog_file)
		ofp = flow_file_utils.open_wfile(verilog_file, force=True)
		ofp.write('module %s (\n' % self.name)
		for pin_num, pin_name in enumerate(grouped_pins):
			ofp.write('\t%s' % (pin_name))
			if pin_num < len(list(grouped_pins)) - 1:
				ofp.write(',')
			ofp.write('\n')
		ofp.write(');\n\n')
		for pin_name, pin_info in grouped_pins.items():
			if pin_info['direction'] == 0:
				ofp.write('input ')
			else:
				ofp.write('output ')
			if pin_info['is_bus']:
				ofp.write('%s%s:%s%s ' % (self.DEF.busBitChars[0], str(pin_info['max_bit']), str(pin_info['min_bit']), self.DEF.busBitChars[1]))
			ofp.write('%s;\n' % (pin_name))
		ofp.write('\n')
		for net_name, net_info in grouped_nets.items():
			ofp.write('wire ')
			if net_info['is_bus']:
				ofp.write('%s%s:%s%s ' % (self.DEF.busBitChars[0], str(net_info['max_bit']), str(net_info['min_bit']), self.DEF.busBitChars[1]))
			ofp.write('%s;\n' % (net_name))
		ofp.write('\n')
		for pin_name in pin_names_excl_pwr_gnd:
			pin_info = self.pins[pin_name]
			if pin_info.net is not None and pin_info.name != pin_info.net.name:
				if pin_info.direction == 0:
					ofp.write('assign %s = %s;\n' % (pin_info.net.name, pin_info.name))
				else:
					ofp.write('assign %s = %s;\n' % (pin_info.name, pin_info.net.name))
		ofp.write('\n')
		for comp_name, comp_info in self.components.items():
			# group component port bits into component bus port
			grouped_compPins = {}
			pin_names_excl_pwr_gnd = list(filter(lambda pin_name: comp_info.macro.pins[pin_name].type != 2 and comp_info.macro.pins[pin_name].type != 3, comp_info.macro.pins.keys()))
			for pin_num, pin_name in enumerate(pin_names_excl_pwr_gnd):
				match = re.match(r'(?P<bus_name>\S+)' + re.escape(self.DEF.busBitChars[0]) + r'(?P<bus_bit>\d+)' + re.escape(self.DEF.busBitChars[1]), pin_name)
				if match is not None:
					bus_name = match['bus_name']
					bus_bit = int(match['bus_bit'])
					if bus_name in grouped_compPins:
						if grouped_compPins[bus_name]['max_bit'] < bus_bit:
							grouped_compPins[bus_name]['max_bit'] = bus_bit
						if grouped_compPins[bus_name]['min_bit'] > bus_bit:
							grouped_compPins[bus_name]['min_bit'] = bus_bit
					else:
						grouped_compPins[bus_name] = {}
						grouped_compPins[bus_name]['is_bus'] = True
						grouped_compPins[bus_name]['direction'] = comp_info.macro.pins[pin_name].direction
						grouped_compPins[bus_name]['max_bit'] = bus_bit
						grouped_compPins[bus_name]['min_bit'] = bus_bit
						grouped_compPins[bus_name]['conn'] = []
				else:
					grouped_compPins[pin_name] = {}
					grouped_compPins[pin_name]['is_bus'] = False
					grouped_compPins[pin_name]['direction'] = comp_info.macro.pins[pin_name].direction

			# establish connections component pins -> nets
			for pin_name, pin_info in grouped_compPins.items():
				if pin_info['is_bus']:
					pin_info['conn'] = ['']*(pin_info['max_bit']-pin_info['min_bit']+1)
				else:
					pin_info['conn'] = ['']
			for pin_num, pin_name in enumerate(pin_names_excl_pwr_gnd):
				match = re.match(r'(?P<bus_name>\S+)' + re.escape(self.DEF.busBitChars[0]) + r'(?P<bus_bit>\d+)' + re.escape(self.DEF.busBitChars[1]), pin_name)
				if match is not None:
					bus_name = match['bus_name']
					bus_bit = int(match['bus_bit'])
					if pin_name in comp_info.pin2net:
						grouped_compPins[bus_name]['conn'][bus_bit-grouped_compPins[bus_name]['min_bit']] = comp_info.pin2net[pin_name].name
					else:
						grouped_compPins[bus_name]['conn'][bus_bit-grouped_compPins[bus_name]['min_bit']] = ''
				else:
					if pin_name in comp_info.pin2net:
						grouped_compPins[pin_name]['conn'] = comp_info.pin2net[pin_name].name
					else:
						grouped_compPins[pin_name]['conn'] = ''

			# write component instantiation statement
			ofp.write('%s %s' % (comp_info.macro.name, comp_name))
			ofp.write('( ')
			for pin_num, pin_name in enumerate(grouped_compPins):
				pin_info = grouped_compPins[pin_name]
				if pin_info['is_bus']:
					ofp.write('.%s(%s)' % (pin_name, '{'+', '.join(reversed(pin_info['conn']))+'}'))
				else:
					ofp.write('.%s(%s)' % (pin_name, pin_info['conn']))
				if pin_num < len(grouped_compPins) - 1:
					ofp.write(',')
				ofp.write(' ')
			ofp.write(');\n')
		ofp.write('\n')
		ofp.write('endmodule\n')
		ofp.close()
		logger.info('writing %s done' % verilog_file)

	def write_3d_top_spef(self, spef_file: str, ilv_R: float, ilv_C: float):
		import datetime
		now = datetime.datetime.now()
		now_str = now.strftime("%d/%m/%Y %H:%M:%S")

		logger.info('start writing spef file %s' % spef_file)
		ofp = flow_file_utils.open_wfile(spef_file, force=True)

		ofp.write("*SPEF \"IEEE 1481-1998\"\n")
		ofp.write("*DESIGN \"%s\"\n" % (self.name))
		ofp.write("*DATE \"%s\"\n" % (now_str))
		ofp.write("*VENDOR \"SKKU DAL\"\n")
		ofp.write("*PROGRAM \"PDFLOW\"\n")
		ofp.write("*VERSION \"1.0\"\n")
		ofp.write("*DESIGN_FLOW \"COUPLING C\" \"PIN_CAP NONE\" \"NAME_SCOPE LOCAL\"\n")
		ofp.write("*DIVIDER /\n")
		ofp.write("*DELIMITER :\n")
		ofp.write("*BUS_DELIMITER []\n")
		ofp.write("*T_UNIT 1 NS\n")
		ofp.write("*C_UNIT 1 PF\n")
		ofp.write("*R_UNIT 1 KOHM\n")
		ofp.write("*L_UNIT 1 HENRY\n")
		ofp.write("\n")
		ofp.write("*NAME_MAP\n")
		ofp.write("\n")

		ofp.write("*PORTS\n")
		for pin_name, pin_info in self.pins.items():
			dir_string = 'I' if pin_info.direction == 0 else 'O'
			ofp.write('%s %s *C 0 0\n' % (pin_name, dir_string))
		ofp.write("\n")

		for net_name, net_info in self.nets.items():
			if re.match(r'^ILV.*', net_name):
				ofp.write('*D_NET %s %f\n' % (net_name, ilv_C))
				ofp.write('*CONN\n')
				ofp.write('*I %s:%s %s *C 0 0\n' % (net_info.compPins[0].comp.name, net_info.compPins[0].pin.name, 'I' if net_info.compPins[0].pin.direction == 0 else 'O'))
				ofp.write('*I %s:%s %s *C 0 0\n' % (net_info.compPins[1].comp.name, net_info.compPins[1].pin.name, 'I' if net_info.compPins[1].pin.direction == 0 else 'O'))
				ofp.write('*CAP\n')
				ofp.write('*I %s:%s %f\n' % (net_info.compPins[0].comp.name, net_info.compPins[0].pin.name, ilv_C/2))
				ofp.write('*I %s:%s %f\n' % (net_info.compPins[1].comp.name, net_info.compPins[1].pin.name, ilv_C/2))
				ofp.write('*RES\n')
				ofp.write('*I %s:%s %s:%s %f\n' % (net_info.compPins[0].comp.name, net_info.compPins[0].pin.name, net_info.compPins[1].comp.name, net_info.compPins[1].pin.name, ilv_R))
				ofp.write('*END\n\n')
		ofp.close()

		'''
		ofile<<"*SPEF \"IEEE 1481-1998\"\n";
		ofile<<"*DESIGN \"top\"\n";
		ofile<<"*DATE \""<<time<<"\"\n";
		ofile<<"*VENDOR \"Shreepad Panth\"\n";
		ofile<<"*PROGRAM \"sp3DWriter (A unified 3D verilog/DEF/SPEF writer)\"\n";
		ofile<<"*VERSION \"1.0\"\n";
		ofile<<"*DESIGN_FLOW \"COUPLING C\" \"PIN_CAP NONE\" \"NAME_SCOPE LOCAL\"\n";
		ofile<<"*DIVIDER /\n";
		ofile<<"*DELIMITER :\n";
		ofile<<"*BUS_DELIMITER []\n";
		ofile<<"*T_UNIT 1 NS\n";
		ofile<<"*C_UNIT 1 PF\n";
		ofile<<"*R_UNIT 1 KOHM\n";
		ofile<<"*L_UNIT 1 HENRY\n";
		ofile<<"\n";
		ofile<<"*NAME_MAP\n";
		ofile << endl;

		// Write out the ports : No parasitics
		ofile<<"*PORTS\n";
		for(int i=0;i<m_nIOPins; i++) {
			string dir = "";
			if (m_vpIOPin[i]->m_eDirection == DIR_INPUT )
				dir = "I";
			else
				dir = "O";
			ofile<< verilogString(m_vpIOPin[i]->m_strName) << " " << dir << " " << " *C 0 0\n";
		}
		ofile << endl;
			// Write out the nets : Each TSV is a top level net
		for(int i=0;i<m_nTSVs; i++) {

			if( m_vpTSV[i]->m_bIsLogic0 || m_vpTSV[i]->m_bIsLogic1 )
				continue;

			// First, get the various parameters
			string netName = verilogString("wire_"+m_vpTSV[i]->m_strName);
			string TSVportName = verilogString(m_vpTSV[i]->m_strName);
			string FSVportName = verilogString("F"+m_vpTSV[i]->m_strName);

			string TSVdir = "";
			string FSVdir = "";
			if ( m_vpTSV[i]->m_eDirection == DIR_INPUT ) {
				TSVdir = "I";
				FSVdir = "O";
			} else {
				TSVdir = "O";
				FSVdir = "I";

			}

			stringstream ssTSVmodule,ssFSVmodule;
			ssTSVmodule << "Udie"<< m_vpTSV[i]->m_nDie ;
			ssFSVmodule << "Udie"<< m_vpTSV[i]->m_nDie + 1;
			string TSVmodule = ssTSVmodule.str();
			string FSVmodule = ssFSVmodule.str();

			// Write out the *DNET section
			ofile <<"*D_NET "<< netName << " " << m_vpTSV[i]->m_dCap <<"\n";
			ofile<<"*CONN\n";
			ofile<<"*I "<<TSVmodule<<":"<<TSVportName<<" "<<TSVdir<<" *C 0 0\n";
			ofile<<"*I "<<FSVmodule<<":"<<FSVportName<<" "<<FSVdir<<" *C 0 0\n";
			ofile<<"*CAP\n";
			ofile<<"1 "<<TSVmodule<<":"<<TSVportName<<" "<<m_vpTSV[i]->m_dCap/2<<"\n";
			ofile<<"2 "<<FSVmodule<<":"<<FSVportName<<" "<<m_vpTSV[i]->m_dCap/2<<"\n";
			ofile<<"*RES\n";
			ofile<<"1 "<<TSVmodule<<":"<<TSVportName<<" "<<FSVmodule<<":"<<FSVportName<<" "
				 <<m_vpTSV[i]->m_dRes<<"\n";
			ofile<<"*END\n";
			ofile<<endl;

		}
		'''
		pass

	def partition_by_pin_comp(self, partitions: List[Set[Union[str, int, float]]] = None, partition_file: str = None, partition_names: List[str] = None) -> 'DEF':
		"""
		partition the specified design based on 'partitions' or 'partition_file'

		:param partitions: list of partitions consisting pins and components (e.g., [(pin1, pin2, comp1, comp2), (pin3, comp3, comp4)] -> pin1, pin2, comp2, comp3 will be in partition_name[0], pin3, comp3, comp4 will be in partition_name[1]
		:param partition_file: path to a file specifying partitions (pin_or_component_name partition_num in each line)
		:param partition_names: name of the resulting partitioned design. if not given, they will be part0, part1, ...
		:return: DEF which consists of partitioned design
		"""
		logger.info('start partition design by its pins and components')
		if partitions is None and partition_file is None:
			logger.error('partitions information or partition_file should be given. return an empty DEF')
			return DEF()
		elif partitions is None and partition_file is not None:
			logger.info('partition design %s with %s' % (self.name, partition_file))
			partitions = []
			ifp = flow_file_utils.open_rfile(os.path.abspath(partition_file))
			for line in ifp:
				comp_name, part = line.split()
				part = int(part)
				if len(partitions) <= part:
					for i in range(len(partitions), part + 1):
						partitions.append(set())
				partitions[part].add(comp_name)
			ifp.close()

		num_partitions = len(partitions)
		part_def = self.DEF.copy(self.name, exclude_wires=True)
		cur_design = part_def.designs[self.name]
		part_design_names = []
		for part_num in range(num_partitions):
			if partition_names is None or part_num >= len(partition_names):
				part_design_names.append('part' + str(part_num))
			else:
				part_design_names.append(partition_names[part_num])
		logger.info('name of the partition\n - %s' % ('\n - '.join(part_design_names)))

		# assign pins and components in each partition
		for part_num, partition in enumerate(partitions):
			part_design_name = part_design_names[part_num]
			logger.info('assigning pins and components to partition %s' % part_design_name)
			part_def.designs[part_design_name] = cur_design.copy_only_header(part_def)
			part_design = part_def.designs[part_design_name]
			part_design.name = part_design_name
			for pin_comp in partition:
				if pin_comp in cur_design.pins:
					part_design.pins[pin_comp] = cur_design.pins[pin_comp]
					part_design.pins[pin_comp]['part'] = part_num
				elif pin_comp in cur_design.components:
					part_design.components[pin_comp] = cur_design.components[pin_comp]
					part_design.components[pin_comp]['part'] = part_num

		# splitting nets crossing partition
		logger.info('splitting nets crossing partitions')
		for net_name, net_info in cur_design.nets.items():
			# calculate how many pins and components (which are connected to this net) are assigned to each partition
			net_info['part_num_pins_comps'] = [0] * num_partitions
			net_num_pins_comps = len(net_info.pins) + len(net_info.compPins)
			for pin in net_info.pins:
				net_info['part_num_pins_comps'][pin['part']] += 1
			for comp_pin in net_info.compPins:
				net_info['part_num_pins_comps'][comp_pin.comp['part']] += 1

			net_crosses_partition = True
			for part_num in range(num_partitions):
				if net_info['part_num_pins_comps'][part_num] == net_num_pins_comps:
					part_def.designs[part_design_names[part_num]].nets[net_name] = net_info
					net_crosses_partition = False

			if net_crosses_partition:
				# identify driver partition
				net_driver_part_num = None
				for pin in net_info.pins:
					if pin.direction == 0:
						net_driver_part_num = pin['part']
						break
				if net_driver_part_num is None:
					for comp_pin in net_info.compPins:
						if comp_pin.pin.direction == 1:
							net_driver_part_num = comp_pin.comp['part']
							break

				# construct subnets for the signals crossing partitions in each partition
				net_driver_design = part_def.designs[part_design_names[net_driver_part_num]]
				net_driver_subnet_info = net_info.copy_only_header(cur_design)
				net_driver_subnet_info.name = net_name
				net_driver_design.nets[net_name] = net_driver_subnet_info
				net_receiver_designs = []
				for part_num in range(num_partitions):
					if part_num != net_driver_part_num and net_info['part_num_pins_comps'][part_num] != 0:
						net_receiver_design = part_def.designs[part_design_names[part_num]]
						net_receiver_subnet_info = net_info.copy_only_header(cur_design)
						net_receiver_subnet_info.name = net_name
						net_receiver_design.nets[net_name] = net_receiver_subnet_info
						net_receiver_designs.append(net_receiver_design)

				# connect related pin to this net
				for pin in net_info.pins:
					pin_design = part_def.designs[part_design_names[pin['part']]]
					pin_design.nets[net_name].pins.append(pin_design.pins[pin.name])
					pin_design.pins[pin.name].net = pin_design.nets[net_name]

				# connect related compPin to this net
				for comp_pin in net_info.compPins:
					comp_pin_design = part_def.designs[part_design_names[comp_pin.comp['part']]]
					subnet_comp_pin = DEFComponentPin()
					subnet_comp_pin.comp = comp_pin_design.components[comp_pin.comp.name]
					subnet_comp_pin.pin = comp_pin_design.components[comp_pin.comp.name].macro.pins[comp_pin.pin.name]
					comp_pin_design.nets[net_name].compPins.append(subnet_comp_pin)
					comp_pin_design.components[comp_pin.comp.name].pin2net[comp_pin.pin.name] = comp_pin_design.nets[net_name]

				net_driver_pin_name = 'FLOWGEN_PART_OUT_' + net_name
				net_driver_design.pins[net_driver_pin_name] = DEFPin()
				net_driver_design.pins[net_driver_pin_name].name = net_driver_pin_name
				net_driver_design.pins[net_driver_pin_name].net = net_driver_design.nets[net_name]
				net_driver_design.pins[net_driver_pin_name].direction = 1
				net_driver_design.pins[net_driver_pin_name].loc = Point(point_type=int)
				net_driver_design.pins[net_driver_pin_name]['parent_net_name'] = net_name
				net_driver_design.nets[net_name].pins.append(net_driver_design.pins[net_driver_pin_name])

				net_receiver_pin_name = 'FLOWGEN_PART_IN_' + net_name
				for net_receiver_design in net_receiver_designs:
					net_receiver_design.pins[net_receiver_pin_name] = DEFPin()
					net_receiver_design.pins[net_receiver_pin_name].name = net_receiver_pin_name
					net_receiver_design.pins[net_receiver_pin_name].net = net_receiver_design.nets[net_name]
					net_receiver_design.pins[net_receiver_pin_name].direction = 0
					net_receiver_design.pins[net_receiver_pin_name].loc = Point(point_type=int)
					net_receiver_design.pins[net_receiver_pin_name]['parent_net_name'] = net_name
					net_receiver_design.nets[net_name].pins.append(net_receiver_design.pins[net_receiver_pin_name])

		del part_def.designs[self.name]

		# generate top design
		part_def.designs[self.name] = part_def.make_top_design_from_sub_designs(top_design_name=self.name)
		logger.info('end partition design')

		return part_def

	def scale(self, scale_factor: float):
		"""
		scale design(size) by scale_factor. all the routing information will be discarded. components and pins locations will be scaled

		:param scale_factor: scale factor (ratio, not percentage) (e.g., if you want to shrink design by 50%, this value should be 0.5)
		"""
		logger.info('scaling design %s by %f' % (self.name, scale_factor))
		self.dieArea.scale(scale_factor, snap_spacing=self.dbUnits*self.DEF.LEF.manufacturingGrid) if self.dieArea is not None else None
		logger.info('fitting row width')
		for row_name in list(self.rows.keys()):
			row_info = self.rows[row_name]
			fit = row_info.fit_width(self.dieArea.rect)
			if not fit:
				del self.rows[row_name]

		# let track/gCellGrids to be reclaculated by the tool
		self.tracks.clear()
		self.gCellGrids.clear()

		logger.info('changing the location of instances')
		for comp_name, comp_info in self.components.items():
			if comp_info.pStatus != -1 or comp_info.pStatus != 3:
				comp_info.loc.scale(scale_factor, snap_spacing=int(self.dbUnits * self.DEF.LEF.manufacturingGrid))

		logger.info('changing the location of pins')
		for pin_name, pin_info in self.pins.items():
			if pin_info.pStatus != -1:
				pin_info.loc.scale(scale_factor, snap_spacing=int(self.dbUnits * self.DEF.LEF.manufacturingGrid))

		logger.info('changing the location of blockages')
		for blockage in self.blockages:
			for shape in blockage.shapes:
				shape.scale(scale_factor, snap_spacing=int(self.dbUnits * self.DEF.LEF.manufacturingGrid))

		for snet_name, snet_info in self.sNets.items():
			snet_info.wires.clear()
		for net_name, net_info in self.nets.items():
			net_info.wires.clear()

		for prop in self.defProps:
			if prop.objType == 2:
				if re.match('FE_CORE_BOX_(LL|UR)_[XY]', prop.name):
					prop.doubleValue = prop.doubleValue * scale_factor

	def split_by_cutLayer(self, split_cutLayer_names: List[str], maps_3d_to_2d: Dict[str, Dict[str, Tuple[int, str]]], split_lef: 'LEF', row_splitting: bool = False, split_names: List[str] = None, exclude_wires: bool = False) -> 'DEF':
		"""
		split the design vertically into multiple design at the given 'split_layer_names'.

		:param split_cutLayer_names: list of layer names which the design is split
		:param maps_3d_to_2d: 3d to 2d name mapping information for layer, via, viarule, site, macro (e.g., {'layer': {'metal1_1':(1, 'metal1')}, 'macro': {'ANDX2_T1':(1, 'ANDX2'}}
		:param split_lef: LEF for split designs
		:param row_splitting: when 3D DEF, whether the design is using half height macros (used in compact2D)
		:param split_names: the name of resulting split designs
		:param exclude_wires: exclude wire shapes from DEF file. connection information will still remain
		:return: new DEF with split design in it
		"""
		logger.info('start splitting design by cut layers: %s' % list(split_cutLayer_names))
		num_splits = len(split_cutLayer_names) + 1
		temp_def = self.DEF.copy(self.name)
		cur_design = temp_def.designs[self.name]
		split_design_names = []
		for split_num in range(num_splits):
			if split_names is None or split_num >= len(split_names):
				split_design_names.append('split' + str(split_num))
			else:
				split_design_names.append(split_names[split_num])
		logger.info('name of the design\n - %s' % ('\n - '.join(split_design_names)))

		# build hypergraph with node: wire segments, via, edge connectivity
		# nets are deleted and created during iteration. use list(self.nets)
		logger.info('start splitting nets in the design')
		num_nets = len(cur_design.nets)
		init_progress(num_nets)

		logger.info('total number of nets in the design: %d' % num_nets)
		for i, net_name in enumerate(list(cur_design.nets)):
			progress_str = get_progress_str(i)
			if progress_str is not None:
				logger.info(progress_str)

			net_info = cur_design.nets[net_name]
			targ_cutLayer_names = net_info.get_existing_cutLayers(split_cutLayer_names)

			# if there are multiple cutLayers to split, it is possible that split net can be split further by other cutLayers
			targ_nets = []
			targ_nets.append(net_info)
			for cutlayer in targ_cutLayer_names:
				subnet_names = []
				for net in targ_nets:
					subnet_names += net.split_by_cutLayer(cutlayer, row_splitting, maps_3d_to_2d['macro'])

				targ_nets = []
				for subnet_name in subnet_names:
					subnet_info = cur_design.nets[subnet_name]
					if len(subnet_info.get_existing_cutLayers(targ_cutLayer_names)) > 0:
						targ_nets.append(subnet_info)

			if len(targ_cutLayer_names) > 0:
				del cur_design.nets[net_name]
		logger.info('end splitting nets')

		logger.info('create split designs')
		split_def = DEF(lef=split_lef)
		split_def.defVersion = temp_def.defVersion
		split_def.dividerChar = temp_def.dividerChar
		split_def.busBitChars = temp_def.busBitChars
		for split_design_name in split_design_names:
			split_design = cur_design.copy_only_header(split_def)
			split_design.name = split_design_name
			if row_splitting:
				split_design.rows = {}
				for split_site_name in split_def.LEF.sites.keys():
					targ_site_names = list(filter(lambda site_name: maps_3d_to_2d['site'][site_name][1] == split_site_name, maps_3d_to_2d['site'].keys()))
					for row_num, row_name_info in enumerate(sorted(filter(lambda name_info: name_info[1].site.name in targ_site_names, cur_design.rows.items()), key=lambda r_name_info: r_name_info[1].origin.y)):
						row_name, row_info = row_name_info
						if row_num % len(split_design_names) == 0:
							merged_row = row_info.copy(split_design)
							merged_row.site = split_design.DEF.LEF.sites[maps_3d_to_2d['site'][row_info.site.name][1]]
							split_design.rows[merged_row.name] = merged_row
			split_design.tracks.clear()
			split_design.gCellGrids.clear()
			# need to handle this
			split_design.vias = {}
			split_design.viarules = {}
			split_def.designs[split_design.name] = split_design

		logger.info('assigning macros in split designs')
		layer_map = {layer_name_3d: tier_layer_name_2d[1] for layer_name_3d, tier_layer_name_2d in maps_3d_to_2d['layer'].items()}
		for comp_name, comp_info in cur_design.components.items():
			comp_tier_num, macro_name_2d = maps_3d_to_2d['macro'][comp_info.macro.name]
			if row_splitting:
				if comp_info.is_shifted_by_row_splitting(comp_tier_num):
					comp_info.loc.y -= int(comp_info.macro.height * cur_design.dbUnits)
			comp_info.macro = split_def.LEF.macros[macro_name_2d]
			split_def.designs[split_design_names[comp_tier_num]].components[comp_name] = comp_info

		logger.info('assigning pins in split designs')
		for pin_name, pin_info in cur_design.pins.items():
			if pin_info.type != 2 and pin_info.type != 3:
				if len(pin_info.shapes) > 0:
					pin_tier_num = maps_3d_to_2d['layer'][pin_info.shapes[0].layer.name][0]
					pin_info.change_layer(layer_map, split_def.LEF)
					pin_info.design = split_def.designs[split_design_names[pin_tier_num]]
					split_def.designs[split_design_names[pin_tier_num]].pins[pin_info.name] = pin_info
				else:
					net = pin_info.net
					pin_tier_num = -1
					for net_pin in net.pins:
						if net_pin.name != pin_name and len(net_pin.shapes) > 0:
							pin_tier_num = maps_3d_to_2d['layer'][net_pin.shapes[0].layer.name][0]
							break
					if pin_tier_num == -1:
						if len(net.compPins) > 0:
							pin_tier_num = maps_3d_to_2d['macro'][net.compPins[0].comp.macro.name][0]
					if pin_tier_num == -1:
						logger.error('tier num for pin %s cannot be determined. ignore this pin' % pin_name)
					else:
						pin_info.design = split_def.designs[split_design_names[pin_tier_num]]
						split_def.designs[split_design_names[pin_tier_num]].pins[pin_info.name] = pin_info

		logger.info('assigning blockages in split designs')
		for blkg in cur_design.blockages:
			if blkg.layer is not None and blkg.layer.name not in split_cutLayer_names:
				blkg_tier_num = maps_3d_to_2d['layer'][blkg.layer.name][0]
				blkg.change_layer(layer_map, split_def.LEF)
				split_def.designs[split_design_names[blkg_tier_num]].blockages.append(blkg)

		logger.info('assigning nets in split designs')
		for net_name, net_info in cur_design.nets.items():
			if len(net_info.wires) > 0 and len(net_info.wires[0].paths) > 0:
				net_tier_num = maps_3d_to_2d['layer'][net_info.wires[0].layer.name][0] if net_info.wires[0].layer is not None else maps_3d_to_2d['layer'][net_info.wires[0].paths[0].layer.name][0]

				if not exclude_wires:
					net_info.change_layer(layer_map, split_def.LEF)
					for wire in net_info.wires:
						for path in wire.paths:
							vias_to_delete = []
							for via in path.vias:
								if via.via.name in maps_3d_to_2d['via']:
									via_tier_num, via_name_2d = maps_3d_to_2d['via'][via.via.name]
									via.via = split_def.LEF.vias[via_name_2d]
								else:
									vias_to_delete.append(via)
							for via_to_delete in vias_to_delete:
								path.vias.remove(via_to_delete)
				else:
					net_info.wires.clear()

				split_def.designs[split_design_names[net_tier_num]].nets[net_name] = net_info
			else:
				net_tier_num = -1
				for net_pin in net_info.pins:
					for tier_num, split_design_name in enumerate(split_design_names):
						if net_pin.name in split_def.designs[split_design_name].pins:
							net_tier_num = tier_num
				if net_tier_num == -1:
					if len(net_info.compPins) > 0:
						for tier_num, split_design_name in enumerate(split_design_names):
							if net_info.compPins[0].comp.name in split_def.designs[split_design_name].components:
								net_tier_num = tier_num
				if net_tier_num == -1:
					logger.error('tier num for net %s cannot be determined. ignore this net' % net_name)
				else:
					split_def.designs[split_design_names[net_tier_num]].nets[net_name] = net_info

		split_def.designs[self.name] = split_def.make_top_design_from_sub_designs(top_design_name=self.name)
		logger.info('end splitting design')
		return split_def

	def make_design_macro(self) -> 'LEFMacro':
		"""
		make LEFMacro for this design

		:return: LEFMacro for this design
		"""
		design_macro = LEFMacro()
		design_macro.name = self.name
		design_macro.macroClass = 13
		design_macro.foreign = self.name
		design_macro.origin = Point(x=0, y=0, point_type=float)
		design_macro.symmetry = 0
		design_macro.site = None
		design_macro.width = (self.dieArea.rect.ur.x - self.dieArea.rect.ll.x) / self.dbUnits
		design_macro.height = (self.dieArea.rect.ur.y - self.dieArea.rect.ll.y) / self.dbUnits
		for pin_name, pin_info in self.pins.items():
			design_macro_pin = LEFMacroPin()
			design_macro_pin.name = pin_name
			design_macro_pin.direction = pin_info.direction
			design_macro_pin.type = pin_info.type
			if design_macro_pin.type > 4:
				design_macro_pin.type = 4
			design_macro_pin.shape = 0
			design_macro_pin.shapes = [shape.copy(self.DEF.LEF.layers) for shape in pin_info.shapes]
			design_macro.pins[design_macro_pin.name] = design_macro_pin
		design_macro.OBSs = []
		return design_macro

	def get_clock_pins_components_nets(self) -> Tuple[List[str], List[str], List[str]]:
		'''
		get list of clock pins, cells and nets in the design (clock cells: clock buffers and clock gates, but NOT flip-flops)

		:return: list of clock pins, list of clock cells, and list of clock nets
		'''
		clock_pins = []
		clock_comps = []
		clock_nets = []
		for net_name, net_info in self.nets.items():
			if net_info.type == 1:
				clock_nets.append(net_name)
				for net_pin in net_info.pins:
					if 'is_clock' not in net_pin:
						net_pin['is_clock'] = 0
					net_pin['is_clock'] += 1
				for net_compPin in net_info.compPins:
					if 'is_clock' not in net_compPin.comp:
						net_compPin.comp['is_clock'] = 0
					net_compPin.comp['is_clock'] += 1
		for pin_name, pin_info in self.pins.items():
			if 'is_clock' in pin_info and pin_info['is_clock'] >= 0:
				clock_pins.append(pin_name)
		for comp_name, comp_info in self.components.items():
			if 'is_clock' in comp_info and comp_info['is_clock'] >= 2:
				# comp_info['is_clock'] == 1 means the component gets clock signal but does not output it
				# that means it is flip-flop.
				# clock buffers and clock gates get clock input as well as produce clock output
				# their comp_info['is_clock'] will be >= 2
				clock_comps.append(comp_name)
		return clock_pins, clock_comps, clock_nets




class DEF:
	"""
	represents DEF
	"""
	LEF: Union['LEF', None]
	'''
	LEF which this DEF is based on
	'''
	swigDEF: Union[LEFDEF.DEF, None]
	'''
	DEF object in LEFDEF C++ library
	'''

	defVersion: str
	'''
	version of DEF
	'''
	dividerChar: str
	'''
	hierarchy divider character
	'''
	busBitChars: str
	'''
	bus bit characters
	'''

	designs: Dict[str, 'DEFDesign']
	'''
	designs in this DEF
	'''
	curDesign: Union[str, None]
	'''
	currently working design name
	'''
	props: Dict[str, Any]
	'''
	user-defined properties
	'''

	def __init__(self, def_file: str = None, lef: 'LEF' = None, exclude_wires: bool = False, verilog_file:str = None):
		"""
		create a DEF

		:param def_file: DEF file to read to construct DEF
		:param lef: LEF which this DEF is based on
		:param exclude_wires: exclude wire shapes from DEF file. connection information will still remain
		"""
		self.defVersion = '5.8'
		self.dividerChar = '/'
		self.busBitChars = '[]'

		self.designs = {}
		self.curDesign = None
		self.hierarchy = {}
		if lef is not None:
			self.set_lef(lef)
			if def_file is not None and verilog_file is None:
				self.read_def(def_file, exclude_wires)
			elif def_file is None and verilog_file is not None:
				self.read_verilog(verilog_file)
				for me, ancester in self.hierarchy.items():
					if len(ancester) != 0 and len(self.hierarchy[ancester[-1]]) != 0:
						self.hierarchy[me] = ancester + self.hierarchy[ancester[-1]]
			else:
				self.swigDEF = None
		else:
			self.LEF = None
			self.swigDEF = None
		self.props = {}

	def __setitem__(self, key, value):
		self.props[key] = value

	def __getitem__(self, item):
		return self.props[item]

	def __contains__(self, item):
		if item in self.props:
			return True
		else:
			return False

	def set_lef(self, lef: 'LEF'):
		"""
		sets LEF which this DEF is based on

		:param lef: LEF which this DEF is based on
		"""
		self.LEF = lef

	def read_def(self, def_file: str, exclude_wires: bool = False):
		"""
		read a DEF file

		:param def_file: DEF file to read
		:param exclude_wires: exclude wire shapes from DEF file. connection information will still remain
		"""
		if os.path.exists(def_file):
			self.swigDEF = self.export()
			logger.info('run LEFDEF SWIG to read %s' % (def_file))
			self.swigDEF.read_def(def_file)
			logger.info('convert DEF to python structure')
			self.import_swigDEF(exclude_wires)
			logger.info('DEF for\n - %s \nis now ready' % (def_file))
		else:
			logger.error('input def file %s does not exists. ignored.' % def_file)
		logger.info('list of designs: %s' % (' '.join(list(self.designs.keys()))))

	def read_verilog(self, verilog_file: str):
		"""
		read a Netlist Verilog file

		:param verilog_file: Verilog file to read
		"""
		if os.path.exists(verilog_file):
			logger.info('read verilog %s' %(verilog_file))
			netlist = verilog_parse.parse_verilog(os.path.join(verilog_file))
			for netlist_module in netlist.modules:
				logger.info('now reading verilog module: %s' %(netlist_module.module_name))
				self.designs[netlist_module.module_name] = DEFDesign(DEF=self, verilog_ref=(netlist_module, netlist.sub_module))
				self.curDesign = netlist_module.module_name
				# self.designs = {netlist_module.module_name: DEFDesign(DEF=self, verilog_ref=(netlist_module, netlist.sub_module))}
		else:
			logger.error('input verilog file %s does not exists. ignored.' %(verilog_file))

	def import_swigDEF(self, exclude_wires: bool = False):
		"""
		convert DEF from LEFDEF C++ library to python DEF structure

		:param exclude_wires: exclude wire shapes from DEF file. connection information will still remain
		"""
		self.defVersion = self.swigDEF.defVersion
		self.dividerChar = self.swigDEF.dividerChar
		self.busBitChars = self.swigDEF.busBitChars

		self.designs = {design_name: DEFDesign(design, self, exclude_wires) for design_name, design in dict(self.swigDEF.designs).items()}
		self.curDesign = self.swigDEF.curDesign

	def export(self, design_name: str = None, floorplan_only: bool = False) -> LEFDEF.DEF:
		"""
		export the DEF to LEFDEF C++ library

		:param design_name: export only the specified design. if None, export all the designs
		:param floorplan_only: the generate def contains only floorplan (no component, no nets, no special net, no pins, no blockage)
		:return: DEF in LEFDEF C++ library
		"""
		targ = LEFDEF.DEF()
		targ.pLEF = self.LEF.swigLEF
		targ.defVersion = self.defVersion
		targ.dividerChar = self.dividerChar
		targ.busBitChars = self.busBitChars

		if design_name is None:
			targ.designs = LEFDEF.MapStrDEFDesign({design_name: design_info.export(targ, floorplan_only) for design_name, design_info in self.designs.items()})
			targ.curDesign = ''
		else:
			if design_name in self.designs:
				targ.designs[design_name] = self.designs[design_name].export(targ, floorplan_only)
				targ.curDesign = design_name
			else:
				logger.error('design %s does not exist' % (design_name))
		return targ

	def copy(self, design_name: str = None, exclude_wires: bool = False) -> 'DEF':
		"""
		copy the object

		:param design_name: copy only the specified design. if None, copy all the designs
		:param exclude_wires: exclude wire shapes from copying. connection information will still remain
		:return: copied object
		"""
		logger.info('start copying DEF')
		cp = DEF()
		cp.LEF = self.LEF.copy()
		cp.defVersion = self.defVersion
		cp.dividerChar = self.dividerChar
		cp.busBitChars = self.busBitChars

		if design_name is None:
			cp.designs = {design_name: design_info.copy(cp, exclude_wires) for design_name, design_info in self.designs.items()}
			cp.curDesign = list(self.designs.keys())[0]
		else:
			if design_name in self.designs:
				cp.designs[design_name] = self.designs[design_name].copy(cp, exclude_wires)
				cp.curDesign = design_name
			else:
				logger.error('design %s does not exist' % (design_name))
		logger.info('end copying DEF')
		return cp

	def make_top_design_from_sub_designs(self, sub_design_names: List[str] = None, top_design_name: str = None) -> 'DEFDesign':
		"""
		make a top design which instantiates designs in this DEF.
		the pins (which are connected between only sub_designs_names) should have 'parent_net_name' property (e.g., DEF.designs[sub_design].pins[pin_name]['parent_net_name'])
		that parent_net_name will be the wire's name which will connect sub designs in the top level.
		the pins don't have 'parent_net_name' property will become top-level pins

		:param sub_design_names: names of the designs in this DEF which will be instantiated in the top design. if None, all the design in this DEF will be instantiated
		:param top_design_name: the name of the top design. if None, the design name will become 'top'
		:return: top design
		"""
		if sub_design_names is None:
			sub_design_names = list(self.designs.keys())
		for sub_design_name in sub_design_names[:]:
			if sub_design_name not in self.designs:
				logger.error('sub design %s does not exist. ignored' % sub_design_name)
				sub_design_names.remove(sub_design_name)

		if top_design_name is None:
			top_design_name = 'top'

		top_design = self.designs[sub_design_names[0]].copy_only_header(self)
		top_design.name = top_design_name
		die_area_llx = float('inf')
		die_area_lly = float('inf')
		die_area_urx = float('-inf')
		die_area_ury = float('-inf')
		for sub_design_name in sub_design_names:
			sub_design = self.designs[sub_design_name]
			if sub_design.dieArea.shape_type == 0:
				# it means dieArea is rect
				if sub_design.dieArea.rect.ll.x < die_area_llx:
					die_area_llx = sub_design.dieArea.rect.ll.x
				if sub_design.dieArea.rect.ll.y < die_area_lly:
					die_area_lly = sub_design.dieArea.rect.ll.y
				if die_area_urx < sub_design.dieArea.rect.ur.x:
					die_area_urx = sub_design.dieArea.rect.ur.x
				if die_area_ury < sub_design.dieArea.rect.ur.y:
					die_area_ury = sub_design.dieArea.rect.ur.y
			else:
				# it means dieArea is polygon
				for pt in sub_design.dieArea.polygon:
					if pt.x < die_area_llx:
						die_area_llx = pt.x
					if pt.y < die_area_lly:
						die_area_lly = pt.y
					if die_area_urx < pt.x:
						die_area_urx = pt.x
					if die_area_ury < pt.y:
						die_area_ury = pt.y

			sub_design_comp = DEFComponent()
			sub_design_comp.name = 'U_' + sub_design_name
			sub_design_comp.macro = sub_design.make_design_macro()
			sub_design_comp.pStatus = 0
			sub_design_comp.orientation = 0
			top_design.components[sub_design_comp.name] = sub_design_comp

		for comp_name, comp_info in top_design.components.items():
			sub_design_name = comp_info.macro.name
			for pin_name, pin_info in self.designs[sub_design_name].pins.items():
				if 'parent_net_name' in pin_info:
					top_net_name = pin_info['parent_net_name']
					top_net_type = 6
				else:
					top_design.pins[pin_name] = pin_info.copy(top_design)
					top_design.pins[pin_name].shapes.clear()
					top_design.pins[pin_name].pStatus = -1

					top_net_name = pin_name
					top_net_type = pin_info.type

				if (top_net_name not in top_design.nets) and (top_net_name not in top_design.sNets):
					top_net = DEFNet()
					top_net.name = top_net_name
					top_net.design = top_design
					top_net.source = 0
					top_net.type = top_net_type
					top_net.routingPattern = 1
					top_net.pins.clear()
					if 'parent_net_name' not in pin_info and (top_net.type == 2 or top_net.type == 3):
						top_design.sNets[top_net.name] = top_net
					else:
						top_design.nets[top_net.name] = top_net

				top_comp_pin = DEFComponentPin()
				top_comp_pin.design = top_design
				top_comp_pin.comp = comp_info
				top_comp_pin.pin = comp_info.macro.pins[pin_name]
				if pin_info.type == 2 or pin_info.type == 3:
					top_design.sNets[top_net_name].compPins.append(top_comp_pin)
					comp_info.pin2net[pin_name] = top_design.sNets[top_net_name]
				else:
					top_design.nets[top_net_name].compPins.append(top_comp_pin)
					comp_info.pin2net[pin_name] = top_design.nets[top_net_name]

		top_design.dieArea = Shape(shape_type=0)
		top_design.dieArea.rect = Rect(llx=round(die_area_llx),
									   lly=round(die_area_lly),
									   urx=round(die_area_urx),
									   ury=round(die_area_ury),
									   rect_type=int)

		for comp_name, comp_info in top_design.components.items():
			comp_info.loc = Point(x=round(die_area_llx), y=round(die_area_lly), point_type=int)

		return top_design

	def make_3d_def(self, impl_type: str, lef_3d: 'LEF', maps_2d_to_3d: Dict[str, List[Dict[str, str]]], design_order: List[str] = None, top_design_name: str = None, row_splitting: bool = False, merge: bool = False) -> 'DEF':
		"""
		from designs in this DEF, make a DEF for 3D ICs (this is used in in pnr 3d_route stage)
		the number of designs in this DEF should be same as number of partitions(tiers) in lef_3d

		:param impl_type: type of 3D IC (f2b or f2f)
		:param lef_3d: 3D LEF for 3D ICs
		:param maps_2d_to_3d: 2d to 3d mapping information for layer, via, viarule, site, macro
		:param design_order:
		:param top_design_name: name of the 3D DEF design. if None, the name will be 'top'
		:param row_splitting: split row into half for half height macros (used in compact2D)
		:return: 3D DEF
		"""
		logger.info('start building 3D DEF by merging the following designs')
		if top_design_name is None:
			top_design_name = 'top'

		logger.info('name of the design\n - %s' % ('\n - '.join(design_order)))
		num_tiers = len(maps_2d_to_3d['layer'])
		num_layers = []
		for tier_num in range(num_tiers):
			num_layers.append(len(list(filter(lambda layer_2d_to_3d: lef_3d.layers[layer_2d_to_3d[1]].type == 2, maps_2d_to_3d['layer'][tier_num].items()))))

		def_3d = DEF(lef=lef_3d)
		def_3d.swigDEF = None
		def_3d.defVersion = self.defVersion
		def_3d.dividerChar = self.dividerChar
		def_3d.busBitChars = self.busBitChars

		ref_design = list(self.designs.values())[0]
		design_3d = ref_design.copy_only_header(def_3d)
		design_3d.name = top_design_name
		if row_splitting:
			design_3d.rows = {}
			for row_name, row_info in ref_design.rows.items():
				if row_info.orientation == 0:
					tier_nums = range(num_tiers)
				else:
					tier_nums = reversed(range(num_tiers))
				cur_y = row_info.origin.y
				for tier_num in tier_nums:
					row_3d = row_info.copy(ref_design)
					row_3d.design = design_3d
					row_3d.site = design_3d.DEF.LEF.sites[maps_2d_to_3d['site'][tier_num][row_info.site.name]]
					row_3d.origin.y = cur_y
					row_3d['tier'] = tier_num
					design_3d.rows[row_name + '_T' + str(tier_num)] = row_3d
					cur_y += int(row_3d.site.height * design_3d.dbUnits)

		'''
		design_3d = DEFDesign()
		design_3d.DEF = def_3d
		design_3d.name = top_design_name
		design_3d.dbUnits = ref_design.dbUnits
		design_3d.defProps = ref_design.defProps.copy()
		design_3d.dieArea = ref_design.dieArea.copy(def_3d.LEF.layers)
		if row_splitting:
			for row_name, row_info in ref_design.rows.items():
				if row_info.orientation == 0:
					tiers = range(num_tiers)
				else:
					tiers = reversed(range(num_tiers))
				cur_y = row_info.origin.y
				for tier_num in tiers:
					row_3d = row_info.copy(ref_design)
					row_3d.design = design_3d
					row_3d.site = design_3d.DEF.LEF.sites[maps_2d_to_3d['site'][tier_num][row_info.site.name]]
					row_3d.origin.y = cur_y
					design_3d.rows[row_name + '_T' + str(tier_num)] = row_3d
					cur_y += int(row_3d.site.height * design_3d.dbUnits)
		else:
			design_3d.rows = {row_name: row.copy(design_3d) for row_name, row in ref_design.rows.items()}
		'''
		design_3d.tracks.clear()
		design_3d.gCellGrids.clear()
		# no need to copy DEF vias, DEF viarules, SNETS as all the wire information is discarded in 3d_route stage
		design_3d.vias.clear()
		design_3d.viarules.clear()

		cutLayer_idx = -1
		for tier_num in range(num_tiers):
			from flow_var_utils import flow_vars as FLOW_VARS
			cur_design = self.designs[design_order[tier_num]]
			logger.info('processing tier %d with design %s' % (tier_num, design_order[tier_num]))
			logger.info('processing components')
			row_height = int
			for comp_name, comp_info in cur_design.components.items():
				comp_3d = comp_info.copy(cur_design)
				comp_3d.change_macro(maps_2d_to_3d['macro'][tier_num], def_3d.LEF)
				if row_splitting:
					if comp_info.is_shifted_by_row_splitting(tier_num):
						comp_3d.loc.y += int(comp_3d.macro.height * design_3d.dbUnits)
				design_3d.components[comp_3d.name] = comp_3d
				if pdflow.has_memory() and comp_info.macro.name in FLOW_VARS['MEMORY_CELLS']:
					pass
				else:
					row_height = comp_info.macro.height

				# make routing blockage on top tier cells if it is f2b 3D IC
				if impl_type == 'f2b' and tier_num != 0:
					blkg = DEFBlkg(design=design_3d)
					blkg.type = 1
					blkg.layer = design_3d.DEF.LEF.cutLayers[cutLayer_idx]
					blkg_shape = Shape()
					blkg_shape.shape_type = 0
					blkg_shape.layer = design_3d.DEF.LEF.cutLayers[cutLayer_idx]
					blkg_shape.rect = Rect(llx=comp_info.loc.x,
										   lly=comp_info.loc.y,
										   urx=comp_info.loc.x + int(comp_info.macro.width * cur_design.dbUnits),
										   ury=comp_info.loc.y + int(comp_info.macro.height * cur_design.dbUnits),
										   rect_type=int)
					blkg.shapes.append(blkg_shape)
					blkg.props['comp'] = comp_3d
					design_3d.blockages.append(blkg)
			cutLayer_idx += num_layers[tier_num]

			logger.info('processing pins')
			to_be_deleted = []
			for pin_name in list(cur_design.pins.keys()):
				pin_info = cur_design.pins[pin_name]
				# if the pin is not power/ground pins
				if pin_info.type != 2 and pin_info.type != 3:
					# if it is a pin to connect partitions
					if merge is False:
						if re.match('FLOWGEN_PART_.*', pin_name):
							# innovus changes net name connected to ILV ports, revert the net name to the original name
							if re.match('FLOWGEN_PART_.*', pin_info.net.name):
								orig_net_name = re.sub('^FLOWGEN_PART_(IN|OUT)_', '', pin_info.net.name)
								cur_design.nets[orig_net_name] = cur_design.nets.pop(pin_info.net.name)
								cur_design.nets[orig_net_name].name = orig_net_name
							# remove the pin from the net
							pin_info.net.pins.remove(pin_info)
							del cur_design.pins[pin_name]
						else:
							pin_3d = pin_info.copy(cur_design)
							pin_3d.change_layer(maps_2d_to_3d['layer'][tier_num], def_3d.LEF)
							design_3d.pins[pin_3d.name] = pin_3d
					elif merge is True:
						if re.match('ILV_(IN|OUT)_', pin_name):
							if re.match('ILV_(IN|OUT)_.*', pin_info.net.name):
								orig_net_name = re.sub('^ILV_(IN|OUT)_', '', pin_info.net.name)
								cur_design.nets[orig_net_name] = cur_design.nets.pop(pin_info.net.name)
								cur_design.nets[orig_net_name].name = orig_net_name
							# remove the pin from the net
							pin_info.net.pins.remove(pin_info)
							del cur_design.pins[pin_name]
						else:
							pin_3d = pin_info.copy(cur_design)
							pin_3d.change_layer(maps_2d_to_3d['layer'][tier_num], def_3d.LEF)
							design_3d.pins[pin_3d.name] = pin_3d

			logger.info('processing blockages')
			for blkg in cur_design.blockages:
				if blkg.type == 0:
					for shape in blkg.shapes:
						for row_name, row_info in design_3d.rows.items():
							if row_info.site.height != row_height / 2:
								continue
							if row_info['tier'] == tier_num:
								blkg_3d = DEFBlkg(design=design_3d)
								blkg_3d.type = 0
								blkg_3d.layer = None
								row_rect = Rect(llx=row_info.origin.x,
													lly=row_info.origin.y,
													urx=row_info.origin.x + row_info.num.x * row_info.step.x,
													ury=row_info.origin.y + row_info.site.height * design_3d.dbUnits,
													rect_type=int)
								blkg_shape = Shape()
								blkg_shape.shape_type = 0
								blkg_shape.layer = None
								blkg_shape.rect = shape.rect.get_intersection(row_rect)
								blkg_3d.shapes.append(blkg_shape)
								design_3d.blockages.append(blkg_3d)
				else:
					blkg_3d = blkg.copy(cur_design)
					blkg_3d.change_layer(maps_2d_to_3d['layer'][tier_num], def_3d.LEF)
					design_3d.blockages.append(blkg_3d)

			# design_3d.sNets.clear()

			logger.info('processing nets')
			if merge is False:
				for net_name, net_info in cur_design.nets.items():
					net_3d = net_info.copy(design_3d, exclude_wires=True)
					if net_name not in design_3d.nets:
						design_3d.nets[net_3d.name] = net_3d
					else:
						design_3d.nets[net_3d.name].pins += net_3d.pins
						design_3d.nets[net_3d.name].compPins += net_3d.compPins
			else:
				logger.info(f'DEF merge: {cur_design.name}')
				is_tier = re.compile(".*_T(\\d)$")
				is_subnet = re.compile("(.*)_SUBNET(\\d)+$")
				for net_name, net_info in cur_design.nets.items():
					net_3d = net_info.copy(design_3d, exclude_wires=False)
					# if re.match('ILV_(IN|OUT)_.*', net_name):
					# 	continue
					if re.match(is_subnet, net_3d.name) is not None:
						net_name = re.sub('.*_SUBNET(\\d)+$', is_subnet.match(net_name).group(1), net_name)
						net_3d.name = net_name
					if len(net_3d.wires) != 0:
						for path, orig_path in zip(net_3d.wires[-1].paths, net_info.wires[-1].paths):
							path.layer = orig_path.layer
							path.vias = orig_path.vias
							if is_tier.match(path.layer.name) is None:
								layer_name = orig_path.layer.name + '_T' + str(tier_num)
								path.layer = lef_3d.layers.get(layer_name)
							elif is_tier.match(path.layer.name).group(1) != tier_num:
								layer_name = orig_path.layer.name + '_T' + str(tier_num)
								path.layer = lef_3d.layers.get(layer_name)
							if len(path.vias) != 0 and is_tier.match(path.vias[0].via.name) is None:
								path_via_name = path.vias[0].via.name + '_T' + str(tier_num)
								path.vias[0].via = lef_3d.vias.get(path_via_name)
							elif len(path.vias) != 0 and is_tier.match(path.vias[0].via.name).group(1) != tier_num:
								path_via_name = path.vias[0].via.name + '_T' + str(tier_num)
								path.vias[0].via = lef_3d.vias.get(path_via_name)
					if net_name not in design_3d.nets:
						design_3d.nets[net_3d.name] = net_3d
					else:
						design_3d.nets[net_3d.name].pins += net_3d.pins
						design_3d.nets[net_3d.name].compPins += net_3d.compPins
						design_3d.nets[net_3d.name].wires += net_3d.wires


		design_3d.connect_pin_net()

		def_3d.designs[top_design_name] = design_3d
		def_3d.curDesign = top_design_name
		logger.info('end building 3D DEF by merging the following designs')

		return def_3d

def convert_maps_2d_to_3d_TO_maps_3d_to_2d(maps_2d_to_3d: Dict[str, List[Dict[str, str]]]) -> Dict[str, Dict[str, Tuple[int, str]]]:
	"""

	:param maps_2d_to_3d: 2d to 3d mapping information for layer, via, viarule, site, macro (produced by make_3d_lef, used in make_3d_def). e.g., {'layer':[{'metal1':'metal1_T0', 'via1':'via1_T0}, {'metal1':'metal1_T0', 'via1':'via1_T0}]}
	:return: 3d to 2d mapping information for layer, via, viarule, site, macro (used in split_vertical) e.g., {'layer':{'metal1_T0':(0, 'metal1'), 'metal1_T1':(1, 'metal1'), 'via1_T0':(0, 'via1'), 'via1_T1':(1, 'via1'}}
	"""
	maps_3d_to_2d = {}
	for key, value in maps_2d_to_3d.items():
		maps_3d_to_2d[key] = {}
		for tier_num, tier_value in enumerate(value):
			for name_2d, name_3d in tier_value.items():
				maps_3d_to_2d[key][name_3d] = (tier_num, name_2d)
	return maps_3d_to_2d



def example_make_3d_def():
	myLEF = LEF(['/Users/kchang/Lab/dal/tech/NANGATE45/2020_10/pdk/lef/NangateOpenCellLibrary.tlef', '/Users/kchang/Lab/dal/tech/NANGATE45/2020_10/cell/lef/NangateOpenCellLibrary.lef'])
	my3DLEF, ilv_layers, maps_2d_to_3d = myLEF.make_3d_lef('f2b', [6, 6], [0.07], [0.07], True)
	my3DLEF.write_lef('/Users/kchang/temp/3d_route/aes_128.lef')
	myPartDEF = DEF(lef=myLEF)
	myPartDEF.read_def('/Users/kchang/temp/3d_legalize/part0.def.gz')
	myPartDEF.read_def('/Users/kchang/temp/3d_legalize/part1.def.gz')
	my3DDEF = myPartDEF.make_3d_def('f2b', my3DLEF, maps_2d_to_3d, ['part0', 'part1'], 'aes_128', True)
	my3DDEF.designs['aes_128'].write_def('/Users/kchang/temp/DEF3D.def')

def example_split_vertical():
	my3DLEF = LEF(['/Users/kchang/temp/3d_route/aes_128.lef'])
	my3DDEF = DEF('/Users/kchang/temp/3d_route/aes_128.def.gz', my3DLEF)
	name_maps = flow_file_utils.read_json_file('/Users/kchang/temp/3d_route/aes_128.map.json')
	maps_3d_to_2d = convert_maps_2d_to_3d_TO_maps_3d_to_2d(name_maps)
	myLEF = LEF(['/Users/kchang/Lab/dal/tech/NANGATE45/2020_10/pdk/lef/NangateOpenCellLibrary.tlef', '/Users/kchang/Lab/dal/tech/NANGATE45/2020_10/cell/lef/NangateOpenCellLibrary.lef'])
	splitDEF = my3DDEF.designs['aes_128'].split_by_cutLayer(['ILV_T01'], maps_3d_to_2d, myLEF, True, ['part0', 'part1'])
	splitDEF.designs['aes_128'].write_verilog('/Users/kchang/temp/3d_route/output/aes_128_split_top.v')
	splitDEF.designs['aes_128'].write_3d_top_spef('/Users/kchang/temp/3d_route/output/aes_128_split_top.spef', 0.01, 0.01)
	splitDEF.designs['part0'].write_verilog('/Users/kchang/temp/3d_route/output/aes_128_split0.v')
	splitDEF.designs['part0'].write_def('/Users/kchang/temp/3d_route/output/aes_128_split0.def')
	splitDEF.designs['part1'].write_verilog('/Users/kchang/temp/3d_route/output/aes_128_split1.v')
	splitDEF.designs['part1'].write_def('/Users/kchang/temp/3d_route/output/aes_128_split1.def')

def example_partition_design():
	myLEF = LEF(['/Users/kchang/Lab/dal/tech/NANGATE45/2020_10/pdk/lef/LowPowerOpenCellLibrary.tlef', '/Users/kchang/Lab/dal/tech/NANGATE45/2020_10/cell/lef/NangateOpenCellLibrary.lef', '/Users/kchang/Lab/dal/tech/NANGATE45/2020_10/cell/lef/LowPowerOpenCellLibrary.lef'])
	myDEF = DEF('/Users/kchang/temp/we/test/aes_128/aes_128/NANGATE45/2020_10/impl/wa_pdn/pnr/finish/results/aes_128.def.gz', myLEF)
	clock_pins, clock_cells, clock_nets = myDEF.designs['aes_128'].get_clock_pins_components_nets()
	partDEF = myDEF.designs['aes_128'].partition_by_pin_comp(partition_file='/Users/kchang/temp/we/test/aes_128/aes_128/NANGATE45/2020_10/impl/wa_pdn/pnr/3d_partition/work/partition_result.txt')
	partDEF.designs['part0'].write_def('/Users/kchang/temp/aes_128_part0.def')
	partDEF.designs['part0'].write_verilog('/Users/kchang/temp/aes_128_part0.v')
	partDEF.designs['part1'].write_def('/Users/kchang/temp/aes_128_part1.def')
	partDEF.designs['part1'].write_verilog('/Users/kchang/temp/aes_128_part1.v')
	partDEF.designs['aes_128'].write_def('/Users/kchang/temp/aes_128_top.def')
	partDEF.designs['aes_128'].write_verilog('/Users/kchang/temp/aes_128_top.v')

def example_scale_macro_lef():
	myLEF = LEF(['/Users/kchang/Lab/dal/tech/NANGATE45/2020_10/pdk/lef/LowPowerOpenCellLibrary.tlef', '/Users/kchang/Lab/dal/dev/scale_macro/input/rfs_64x84_wm0.lef'])
	#myLEF = LEF(['/Users/kchang/Lab/dal/tech/NANGATE45/2020_10/pdk/lef/LowPowerOpenCellLibrary.tlef', '/Users/kchang/Lab/dal/tech/NANGATE45/2020_10/cell/lef/NangateOpenCellLibrary.lef'])
	myLEF.write_lef(lef_file='/Users/kchang/Lab/dal/dev/scale_macro/output/original.lef', only_macro=True)
	myLEF.scale_macro(scale_factor=0.33333)
	myLEF.write_lef(lef_file='/Users/kchang/Lab/dal/dev/scale_macro/output/scaled.lef', only_macro=True)

def example_make_3d_lef():
	myLEF = LEF(['/Users/kchang/Lab/dal/tech/CLN28HPM/r4p0/pdk/lef/sc12mc_tech.lef', '/Users/kchang/Lab/dal/tech/CLN28HPM/r4p0/cell/lef/sc12mc_cln28hpm_base_hvt_c35.lef'])
	i3DLEF, ilv_layers, maps_2d_to_3d = myLEF.make_3d_lef('f2b', [6, 6], [0.7, 0.7], [0.7, 0.7], True)
	pass

def example_partial_blkg():
	myLEF = LEF(['/Users/kchang/Lab/dal/tech/NANGATE45/2020_10/pdk/lef/LowPowerOpenCellLibrary.tlef', '/Users/kchang/Lab/dal/tech/NANGATE45/2020_10/cell/lef/NangateOpenCellLibrary.lef', '/Users/kchang/Lab/dal/tech/NANGATE45/2020_10/cell/lef/LowPowerOpenCellLibrary.lef'])
	myDEF = DEF('/Users/kchang/temp/init/aes_128.init.def', myLEF)

	myPtLL = Point()
	myPtLL.point_type = int
	myPtUR = Point()
	myPtUR.point_type = int

	myRect = Rect()
	myRect.rect_type = int
	myRect.ll = myPtLL
	myRect.ur = myPtUR

	myShape = Shape()
	myShape.shape_type = 0
	myShape.layer = None
	myShape.rect = myRect
	myShape.rect.ll.x = 0
	myShape.rect.ll.y = 0
	myShape.rect.ur.x = 2000
	myShape.rect.ur.y = 2000

	blkg = DEFBlkg()
	blkg.type = 0
	blkg.layer = None
	blkg.shapes.append(myShape)
	myDEF.designs['aes_128'].blockages.append(blkg)

	blkg = DEFBlkg()
	blkg.type = 0
	blkg.layer = None
	blkg.partial = 30
	blkg.shapes.append(myShape)
	myDEF.designs['aes_128'].blockages.append(blkg)

	myDEF.designs['aes_128'].write_def('/Users/kchang/temp/init/aes_128.add_blkg_python.def')


def example_write_verilog():
	myLEF = LEF(['/Users/kchang/Lab/dal/tech/CLN28HPM_BASE/r4p0/pdk/lef/sc12mc_tech.lef', '/Users/kchang/Lab/dal/tech/CLN28HPM_BASE/r4p0/cell/lef/sc12mc_cln28hpm_base_lvt_c35.lef', '/Users/kchang/Lab/dal/tech/CLN28HPM_BASE/r4p0/cell/lef/sc12mc_cln28hpm_base_ulvt_c35.lef', '/Users/kchang/Lab/dal/tech/CLN28HPM/r4p0/memory/lef/rf_sp_32x16.lef'])
	myDEF = DEF('/Users/kchang/temp/lefdef_verilog/mem_test.def.gz', myLEF)
	myDEF.designs['mem_test'].write_verilog('/Users/kchang/temp/lefdef_verilog/mem_test.v')


def example_read_verilog():
	myLEF = LEF(['/Users/kchang/Lab/dal/tech/CLN28HPM_BASE/r4p0/pdk/lef/sc12mc_tech.lef', '/Users/kchang/Lab/dal/tech/CLN28HPM_BASE/r4p0/cell/lef/sc12mc_cln28hpm_base_lvt_c35.lef', '/Users/kchang/Lab/dal/tech/CLN28HPM_BASE/r4p0/cell/lef/sc12mc_cln28hpm_base_ulvt_c35.lef', '/Users/kchang/Lab/dal/tech/CLN28HPM/r4p0/memory/lef/rf_sp_32x16.lef'])
	myDEF = DEF(lef=myLEF)
	myDEF.read_verilog('/Users/kchang/temp/lefdef_verilog/mem_test.slash_removed.v')
	myDEF.designs['mem_test'].write_verilog('/Users/kchang/temp/lefdef_verilog/mem_test.output.v')
	pass

def merge_def_for_analysis():
	lef_path = ['/Users/parkjuseong/Desktop/test/sc12mc_tech.lef', \
				'/Users/parkjuseong/Desktop/test/sc12mc_cln28hpm_base_hvt_c35.lef', \
				'/Users/parkjuseong/Desktop/test/sc12mc_cln28hpm_base_lvt_c35.lef', \
				'/Users/parkjuseong/Desktop/test/sc12mc_cln28hpm_base_uhvt_c35.lef', \
				'/Users/parkjuseong/Desktop/test/sc12mc_cln28hpm_base_ulvt_c35.lef', \
				'/Users/parkjuseong/Desktop/test/sc12mc_cln28hpm_hpk_hvt_c35.lef', \
				'/Users/parkjuseong/Desktop/test/sc12mc_cln28hpm_hpk_ulvt_c35.lef', \
				'/Users/parkjuseong/Desktop/test/sc12mc_cln28hpm_pmk_hvt_c35.lef', \
				'/Users/parkjuseong/Desktop/test/sc12mc_cln28hpm_pmk_lvt_c35.lef', \
				'/Users/parkjuseong/Desktop/test/sc12mc_cln28hpm_pmk_svt_c35.lef', \
				'/Users/parkjuseong/Desktop/test/rf_sp_32x16.lef', \
				'/Users/parkjuseong/Desktop/test/sc12mc_cln28hpm_pmk_svt_c35.lef']
	lLEF = LEF(lef_files=lef_path)
	lDEF = DEF(lef=lLEF)
	lDEF.read_def('/Users/parkjuseong/Desktop/test/part0.def.gz')
	lDEF.read_def('/Users/parkjuseong/Desktop/test/part1.def.gz')
	i3DLEF, ilv_layers, maps_2d_to_3d = lLEF.make_3d_lef('f2b', [6, 6], [0.07], [0.07], True)
	i3DLEF.write_lef('Users/parkjuseong/Desktop/test/mem_test_3d.lef')

	i3DDEF = lDEF.make_3d_def('f2b', i3DLEF, maps_2d_to_3d, ['part0', 'part1'], 'mem_test', True, True)
	i3DDEF.designs['mem_test'].write_def('/Users/parkjuseong/Desktop/test/DEF_3D.def')

if __name__ == '__main__':
	#example_split_vertical()
	#example_partial_blkg()
	# example_partition_design()
	#example_scale_macro_lef()
	#example_make_3d_lef()
	#example_write_verilog()
	# example_read_verilog()
	merge_def_for_analysis()
	pass
