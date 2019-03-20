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

/** \file gameengine/Rasterizer/RAS_EffectsManager.cpp
*  \ingroup bgerast
*/

#include "RAS_ICanvas.h"
#include "RAS_Rasterizer.h"
#include "RAS_OffScreen.h"
#include "RAS_EffectsManager.h"

#include "BLI_math.h"

#include "KX_Scene.h"
#include "KX_Camera.h"
#include "KX_Globals.h"

extern "C" {
#  include "GPU_framebuffer.h"
}

RAS_EffectsManager::RAS_EffectsManager(RAS_ICanvas *canvas, KX_Scene *scene):
	m_scene(scene),
	m_canvas(canvas)
{
	m_compositor = GPU_fx_compositor_create();
	const int *viewport = m_canvas->GetViewPort();
	m_rect.xmin = viewport[0];
	m_rect.ymin = viewport[1];
	m_rect.xmax = viewport[2];
	m_rect.ymax = viewport[3];

	GPU_fx_compositor_init_ssao_settings(&m_ssaoSettings);
	// TODO same for DOF;

	m_compositorSettings.ssao = &m_ssaoSettings;
	m_compositorSettings.fx_flag |= GPU_FX_FLAG_SSAO;
	m_compositorSettings.fx_flag &= ~GPU_FX_FLAG_DOF;

	GPU_fx_compositor_initialize_passes(m_compositor, &m_rect, &m_rect, &m_compositorSettings);

	m_offScreen = GPU_offscreen_create(viewport[2], viewport[3], 0, nullptr);
}

RAS_EffectsManager::~RAS_EffectsManager()
{
	GPU_fx_compositor_destroy(m_compositor);
	//GPU_offscreen_free(m_offScreen);
}

RAS_OffScreen *RAS_EffectsManager::RenderEffects(RAS_Rasterizer *rasty, RAS_OffScreen *inputofs)
{
	rasty->Disable(RAS_Rasterizer::RAS_DEPTH_TEST);

	/* try only AO for now  */
	if (1) {
		KX_Camera *cam = m_scene->GetActiveCamera();
		float projmat[4][4];
		cam->GetProjectionMatrix(RAS_Rasterizer::RAS_STEREO_LEFTEYE).Pack(projmat);

		GPU_offscreen_attach_color(m_offScreen, inputofs->GetMainColorTexture());
		GPU_offscreen_attach_depth(m_offScreen, inputofs->GetDepthTexture());

		GPU_fx_do_composite_pass(m_compositor, projmat, true, m_scene->GetBlenderScene(), m_offScreen);

		GPU_offscreen_detach_color(m_offScreen);
		GPU_offscreen_detach_depth(m_offScreen);

		return inputofs;
	}

	rasty->Enable(RAS_Rasterizer::RAS_DEPTH_TEST);

	return inputofs;
}
