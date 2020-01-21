/*
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
 * Copyright 2019, Blender Foundation.
 */

/** \file
 * \ingroup draw
 */

#include "DRW_render.h"

#include "eevee_engine.h"
#include "eevee_private.h"

#include "smaa_textures.h"

static struct {
  struct GPUShader *antialiasing_sh[3];
} e_data = {NULL}; /* Engine data */

extern char datatoc_antialiasing_frag_glsl[];
extern char datatoc_antialiasing_vert_glsl[];
extern char datatoc_common_smaa_lib_glsl[];

static struct GPUShader *eevee_create_shader_antialiasing(int stage)
{
  BLI_assert(stage < 3);

  if (!e_data.antialiasing_sh[stage]) {
    char stage_define[32];
    BLI_snprintf(stage_define, sizeof(stage_define), "#define SMAA_STAGE %d\n", stage);

    e_data.antialiasing_sh[stage] = GPU_shader_create_from_arrays({
        .vert =
            (const char *[]){
                "#define SMAA_INCLUDE_VS 1\n",
                "#define SMAA_INCLUDE_PS 0\n",
                "uniform vec4 viewportMetrics;\n",
                datatoc_common_smaa_lib_glsl,
                datatoc_antialiasing_vert_glsl,
                NULL,
            },
        .frag =
            (const char *[]){
                "#define SMAA_INCLUDE_VS 0\n",
                "#define SMAA_INCLUDE_PS 1\n",
                "uniform vec4 viewportMetrics;\n",
                datatoc_common_smaa_lib_glsl,
                datatoc_antialiasing_frag_glsl,
                NULL,
            },
        .defs =
            (const char *[]){
                "#define SMAA_GLSL_3\n",
                "#define SMAA_RT_METRICS viewportMetrics\n",
                "#define SMAA_PRESET_ULTRA\n",
                stage_define,
                NULL,
            },
    });
  }
  return e_data.antialiasing_sh[stage];
}

void EEVEE_antialiasing_init(struct EEVEE_Data *vedata)
{
  EEVEE_PrivateData *g_data = vedata->stl->g_data;
  EEVEE_FramebufferList *fbl = vedata->fbl;
  EEVEE_TextureList *txl = vedata->txl;
  EEVEE_PassList *psl = vedata->psl;
  DRWShadingGroup *grp;

  /* We need a temporary buffer to output result. */
  BLI_assert(g_data->color_layer_tx && g_data->reveal_layer_tx);

  if (txl->smaa_search_tx == NULL) {
    txl->smaa_search_tx = GPU_texture_create_nD(SEARCHTEX_WIDTH,
                                                SEARCHTEX_HEIGHT,
                                                0,
                                                2,
                                                searchTexBytes,
                                                GPU_R8,
                                                GPU_DATA_UNSIGNED_BYTE,
                                                0,
                                                false,
                                                NULL);

    txl->smaa_area_tx = GPU_texture_create_nD(AREATEX_WIDTH,
                                              AREATEX_HEIGHT,
                                              0,
                                              2,
                                              areaTexBytes,
                                              GPU_RG8,
                                              GPU_DATA_UNSIGNED_BYTE,
                                              0,
                                              false,
                                              NULL);

    GPU_texture_bind(txl->smaa_search_tx, 0);
    GPU_texture_filter_mode(txl->smaa_search_tx, true);
    GPU_texture_unbind(txl->smaa_search_tx);

    GPU_texture_bind(txl->smaa_area_tx, 0);
    GPU_texture_filter_mode(txl->smaa_area_tx, true);
    GPU_texture_unbind(txl->smaa_area_tx);
  }

  const float *size = DRW_viewport_size_get();
  float metrics[4] = {1.0f / size[0], 1.0f / size[1], size[0], size[1]};

  {
    g_data->smaa_edge_tx = DRW_texture_pool_query_2d(
        size[0], size[1], GPU_RG8, &draw_engine_eevee_type);
    g_data->smaa_weight_tx = DRW_texture_pool_query_2d(
        size[0], size[1], GPU_RGBA8, &draw_engine_eevee_type);

    GPU_framebuffer_ensure_config(&fbl->smaa_edge_fb,
                                  {
                                      GPU_ATTACHMENT_NONE,
                                      GPU_ATTACHMENT_TEXTURE(g_data->smaa_edge_tx),
                                  });

    GPU_framebuffer_ensure_config(&fbl->smaa_weight_fb,
                                  {
                                      GPU_ATTACHMENT_NONE,
                                      GPU_ATTACHMENT_TEXTURE(g_data->smaa_weight_tx),
                                  });
  }

  {
    /* Stage 1: Edge detection. */
    DRW_PASS_CREATE(psl->smaa_edge_ps, DRW_STATE_WRITE_COLOR);

    GPUShader *sh = eevee_create_shader_antialiasing(0);
    grp = DRW_shgroup_create(sh, psl->smaa_edge_ps);
    DRW_shgroup_uniform_texture(grp, "colorTex", g_data->smaa_edge_tx);
    DRW_shgroup_uniform_texture(grp, "revealTex", g_data->smaa_weight_tx);
    DRW_shgroup_uniform_vec4_copy(grp, "viewportMetrics", metrics);

    DRW_shgroup_clear_framebuffer(grp, GPU_COLOR_BIT, 0, 0, 0, 0, 0.0f, 0x0);
    DRW_shgroup_call_procedural_triangles(grp, NULL, 1);
  }
  {
    /* Stage 2: Blend Weight/Coord. */
    DRW_PASS_CREATE(psl->smaa_weight_ps, DRW_STATE_WRITE_COLOR);

    GPUShader *sh = eevee_create_shader_antialiasing(1);
    grp = DRW_shgroup_create(sh, psl->smaa_weight_ps);
    DRW_shgroup_uniform_texture(grp, "edgesTex", g_data->smaa_edge_tx);
    DRW_shgroup_uniform_texture(grp, "areaTex", txl->smaa_area_tx);
    DRW_shgroup_uniform_texture(grp, "searchTex", txl->smaa_search_tx);
    DRW_shgroup_uniform_vec4_copy(grp, "viewportMetrics", metrics);

    DRW_shgroup_clear_framebuffer(grp, GPU_COLOR_BIT, 0, 0, 0, 0, 0.0f, 0x0);
    DRW_shgroup_call_procedural_triangles(grp, NULL, 1);
  }
  {
    /* Stage 3: Resolve. */
    /* TODO merge it with the main composite pass. */
    DRW_PASS_CREATE(psl->smaa_resolve_ps, DRW_STATE_WRITE_COLOR);

    GPUShader *sh = eevee_create_shader_antialiasing(2);
    grp = DRW_shgroup_create(sh, psl->smaa_resolve_ps);
    DRW_shgroup_uniform_texture(grp, "blendTex", g_data->smaa_weight_tx);
    DRW_shgroup_uniform_texture(grp, "colorTex", g_data->color_tx);
    DRW_shgroup_uniform_texture(grp, "revealTex", g_data->reveal_tx);
    DRW_shgroup_uniform_vec4_copy(grp, "viewportMetrics", metrics);

    DRW_shgroup_call_procedural_triangles(grp, NULL, 1);
  }
}

void EEVEE_antialiasing_draw(struct EEVEE_Data *vedata)
{
  EEVEE_FramebufferList *fbl = vedata->fbl;
  EEVEE_PrivateData *g_data = vedata->stl->g_data;
  EEVEE_PassList *psl = vedata->psl;

  GPU_framebuffer_bind(fbl->smaa_edge_fb);
  DRW_draw_pass(psl->smaa_edge_ps);

  GPU_framebuffer_bind(fbl->smaa_weight_fb);
  DRW_draw_pass(psl->smaa_weight_ps);

  GPU_framebuffer_bind(fbl->layer_fb);
  DRW_draw_pass(psl->smaa_resolve_ps);

  /* Swap buffers */
  SWAP(GPUTexture *, g_data->color_tx, g_data->color_layer_tx);
  SWAP(GPUTexture *, g_data->reveal_tx, g_data->reveal_layer_tx);
}

void EEVEE_antialiasing_free(void)
{
  for (int i = 0; i < 3; i++) {
    DRW_SHADER_FREE_SAFE(e_data.antialiasing_sh[i]);
  }
}
