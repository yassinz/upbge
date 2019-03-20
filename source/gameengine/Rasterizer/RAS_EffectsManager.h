/*
* ***** BEGIN GPL LICENSE BLOCK *****
*
* This program is free software; you can redistribute it and/or
* modify it under the terms of the GNU General Public License
* as published by the Free Software Foundation; either version 2
* of the License, or (at your option) any later version.
*
* This program is distributed in the hope that it will be useful,
* but WITHOUT ANY WARRANTY; without even the implied warranty of
* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
* GNU General Public License for more details.
*
* You should have received a copy of the GNU General Public License
* along with this program; if not, write to the Free Software Foundation,
* Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
*
* Contributor(s):
*
* ***** END GPL LICENSE BLOCK *****
*/

/** \file RAS_EffectsManager.h
*  \ingroup bgerast
*/

#ifndef __RAS_EFFECTSMANAGER_H__
#define __RAS_EFFECTSMANAGER_H__

extern "C" {
#  include "DNA_gpu_types.h"
#  include "DNA_vec_types.h"
#  include "GPU_compositing.h"
}

class RAS_ICanvas;
class RAS_OffScreen;
class KX_Scene;

struct GPUFX;
struct GPUOffScreen;
struct rcti;

class RAS_EffectsManager
{

public:
	RAS_EffectsManager(RAS_ICanvas *canvas, KX_Scene *scene);
	virtual ~RAS_EffectsManager();

	RAS_OffScreen *RenderEffects(RAS_Rasterizer *rasty, RAS_OffScreen *inputofs);

private:

	KX_Scene *m_scene;

	RAS_ICanvas *m_canvas; // used to get viewport size

	GPUFX *m_compositor;
	GPUFXSettings m_compositorSettings;
	GPUSSAOSettings m_ssaoSettings;

	GPUOffScreen *m_offScreen;

	rcti m_rect;
};

#endif // __RAS_EFFECTSMANAGER_H__
