# ***** BEGIN GPL LICENSE BLOCK *****
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# The Original Code is Copyright (C) 2006, Blender Foundation
# All rights reserved.
#
# The Original Code is: all of this file.
#
# Contributor(s): Jacques Beaurain.
#
# ***** END GPL LICENSE BLOCK *****

# since this includes bullet we get errors from the headers too
remove_strict_flags()

set(INC
	.
	../Common
	../../Common
	../../Converter
	../../Expressions
	../../GameLogic
	../../Ketsji
	../../Rasterizer
	../../SceneGraph
	../../../blender/blenkernel
	../../../blender/blenlib
	../../../blender/draw/engines/eevee/
	../../../blender/gpu
	../../../blender/makesdna
	../../../../intern/guardedalloc
)

set(INC_SYS
	../../../../intern/moto/include
	${PYTHON_INCLUDE_DIRS}
	${BOOST_INCLUDE_DIR}
)

set(SRC
	CcdConstraint.cpp
	CcdPhysicsEnvironment.cpp
	CcdPhysicsController.cpp
	CcdGraphicController.cpp

	CcdConstraint.h
	CcdMathUtils.h
	CcdGraphicController.h
	CcdPhysicsController.h
	CcdPhysicsEnvironment.h
)

set(LIB
)

if(WITH_BULLET)
	list(APPEND INC_SYS
		${BULLET_INCLUDE_DIRS}
	)
	add_definitions(-DWITH_BULLET)
        list(APPEND LIB
          extern_bullet
        )
endif()

add_definitions(${GL_DEFINITIONS})

blender_add_lib(ge_physics_bullet "${SRC}" "${INC}" "${INC_SYS}" "${LIB}")
