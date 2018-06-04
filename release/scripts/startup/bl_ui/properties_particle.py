# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

# <pep8 compliant>
import bpy
from bpy.types import Panel, Menu
from rna_prop_ui import PropertyPanel
from bpy.app.translations import pgettext_iface as iface_

from .properties_physics_common import (
    point_cache_ui,
    effector_weights_ui,
    basic_force_field_settings_ui,
    basic_force_field_falloff_ui,
)


def particle_panel_enabled(context, psys):
    if psys is None:
        return True
    phystype = psys.settings.physics_type
    if psys.settings.type in {'EMITTER', 'REACTOR'} and phystype in {'NO', 'KEYED'}:
        return True
    else:
        return (psys.point_cache.is_baked is False) and (not psys.is_edited) and (not context.particle_system_editable)


def particle_panel_poll(cls, context):
    psys = context.particle_system
    engine = context.engine
    settings = 0

    if psys:
        settings = psys.settings
    elif isinstance(context.space_data.pin_id, bpy.types.ParticleSettings):
        settings = context.space_data.pin_id

    if not settings:
        return False

    return settings.is_fluid is False and (engine in cls.COMPAT_ENGINES)


def particle_get_settings(context):
    if context.particle_system:
        return context.particle_system.settings
    elif isinstance(context.space_data.pin_id, bpy.types.ParticleSettings):
        return context.space_data.pin_id
    return None


class PARTICLE_MT_specials(Menu):
    bl_label = "Particle Specials"
    COMPAT_ENGINES = {'BLENDER_RENDER', 'BLENDER_GAME', 'BLENDER_CLAY', 'BLENDER_EEVEE'}

    def draw(self, context):
        layout = self.layout

        props = layout.operator("particle.copy_particle_systems", text="Copy Active to Selected Objects")
        props.use_active = True
        props.remove_target_particles = False

        props = layout.operator("particle.copy_particle_systems", text="Copy All to Selected Objects")
        props.use_active = False
        props.remove_target_particles = True

        layout.operator("particle.duplicate_particle_system")


class PARTICLE_MT_hair_dynamics_presets(Menu):
    bl_label = "Hair Dynamics Presets"
    preset_subdir = "hair_dynamics"
    preset_operator = "script.execute_preset"
    COMPAT_ENGINES = {'BLENDER_RENDER', 'BLENDER_GAME', 'BLENDER_CLAY', 'BLENDER_EEVEE'}
    draw = Menu.draw_preset


class ParticleButtonsPanel:
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "particle"

    @classmethod
    def poll(cls, context):
        return particle_panel_poll(cls, context)


def find_modifier(ob, psys):
    for md in ob.modifiers:
        if md.type == 'PARTICLE_SYSTEM':
            if md.particle_system == psys:
                return md


class PARTICLE_UL_particle_systems(bpy.types.UIList):

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index, flt_flag):
        ob = data
        psys = item

        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            md = find_modifier(ob, psys)

            layout.prop(psys, "name", text="", emboss=False, icon_value=icon)
            if md:
                layout.prop(md, "show_render", emboss=False, icon_only=True,
                            icon='RESTRICT_RENDER_OFF' if md.show_render else 'RESTRICT_RENDER_ON')
                layout.prop(md, "show_viewport", emboss=False, icon_only=True,
                            icon='RESTRICT_VIEW_OFF' if md.show_viewport else 'RESTRICT_VIEW_ON')

        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text="", icon_value=icon)


class PARTICLE_PT_context_particles(ParticleButtonsPanel, Panel):
    bl_label = ""
    bl_options = {'HIDE_HEADER'}
    COMPAT_ENGINES = {'BLENDER_RENDER', 'BLENDER_GAME', 'BLENDER_CLAY', 'BLENDER_EEVEE'}

    @classmethod
    def poll(cls, context):
        engine = context.engine
        return (context.particle_system or context.object or context.space_data.pin_id) and (engine in cls.COMPAT_ENGINES)

    def draw(self, context):
        layout = self.layout

        if context.engine == 'BLENDER_GAME':
            layout.label("Not available in the Game Engine")
            return

        ob = context.object
        psys = context.particle_system
        part = 0

        if ob:
            row = layout.row()

            row.template_list("PARTICLE_UL_particle_systems", "particle_systems", ob, "particle_systems",
                              ob.particle_systems, "active_index", rows=1)

            col = row.column(align=True)
            col.operator("object.particle_system_add", icon='ZOOMIN', text="")
            col.operator("object.particle_system_remove", icon='ZOOMOUT', text="")
            col.menu("PARTICLE_MT_specials", icon='DOWNARROW_HLT', text="")

        if psys is None:
            part = particle_get_settings(context)

            layout.operator("object.particle_system_add", icon='ZOOMIN', text="New")

            if part is None:
                return

            layout.template_ID(context.space_data, "pin_id")

            if part.is_fluid:
                layout.label(text="Settings used for fluid")
                return

            layout.prop(part, "type", text="Type")

        elif not psys.settings:
            split = layout.split(percentage=0.32)

            col = split.column()
            col.label(text="Settings:")

            col = split.column()
            col.template_ID(psys, "settings", new="particle.new")
        else:
            part = psys.settings

            split = layout.split(percentage=0.32)
            col = split.column()
            if part.is_fluid is False:
                col.label(text="Settings:")
                col.label(text="Type:")

            col = split.column()
            if part.is_fluid is False:
                row = col.row()
                row.enabled = particle_panel_enabled(context, psys)
                row.template_ID(psys, "settings", new="particle.new")

            if part.is_fluid:
                layout.label(text=iface_("%d fluid particles for this frame") % part.count, translate=False)
                return

            row = col.row()
            row.enabled = particle_panel_enabled(context, psys)
            row.prop(part, "type", text="")
            row.prop(psys, "seed")

        if part:
            split = layout.split(percentage=0.65)
            if part.type == 'HAIR':
                if psys is not None and psys.is_edited:
                    split.operator("particle.edited_clear", text="Free Edit")
                else:
                    row = split.row()
                    row.enabled = particle_panel_enabled(context, psys)
                    row.prop(part, "regrow_hair")
                    row.prop(part, "use_advanced_hair")
                row = split.row()
                row.enabled = particle_panel_enabled(context, psys)
                row.prop(part, "hair_step")
                if psys is not None and psys.is_edited:
                    if psys.is_global_hair:
                        row = layout.row(align=True)
                        row.operator("particle.connect_hair").all = False
                        row.operator("particle.connect_hair", text="Connect All").all = True
                    else:
                        row = layout.row(align=True)
                        row.operator("particle.disconnect_hair").all = False
                        row.operator("particle.disconnect_hair", text="Disconnect All").all = True
            elif psys is not None and part.type == 'REACTOR':
                split.enabled = particle_panel_enabled(context, psys)
                split.prop(psys, "reactor_target_object")
                split.prop(psys, "reactor_target_particle_system", text="Particle System")


class PARTICLE_PT_emission(ParticleButtonsPanel, Panel):
    bl_label = "Emission"
    COMPAT_ENGINES = {'BLENDER_RENDER', 'BLENDER_CLAY', 'BLENDER_EEVEE'}

    @classmethod
    def poll(cls, context):
        psys = context.particle_system
        settings = particle_get_settings(context)

        if settings is None:
            return False
        if settings.is_fluid:
            return False
        if particle_panel_poll(PARTICLE_PT_emission, context):
            return psys is None or not context.particle_system.point_cache.use_external
        return False

    def draw(self, context):
        layout = self.layout

        psys = context.particle_system
        part = particle_get_settings(context)

        layout.use_property_split = True

        layout.enabled = particle_panel_enabled(context, psys) and (psys is None or not psys.has_multiple_caches)

        col = layout.column()
        col.active = part.emit_from == 'VERT' or part.distribution != 'GRID'
        col.prop(part, "count")

        if part.type == 'HAIR':
            col.prop(part, "hair_length")
            if not part.use_advanced_hair:
                row = layout.row()
                col.prop(part, "use_modifier_stack")
                return

        if part.type != 'HAIR':

            col = layout.column()

            sub = col.column(align=True)
            sub.prop(part, "frame_start", text="Frame Start")
            sub.prop(part, "frame_end", text="End")

            col.prop(part, "lifetime")
            col.prop(part, "lifetime_random", slider=True, text="Lifetime Randomness")


class PARTICLE_PT_emission_source(ParticleButtonsPanel, Panel):
    bl_label = "Source"
    bl_parent_id = "PARTICLE_PT_emission"
    COMPAT_ENGINES = {'BLENDER_RENDER', 'BLENDER_CLAY', 'BLENDER_EEVEE'}

    def draw(self, context):
        layout = self.layout

        part = particle_get_settings(context)

        layout.use_property_split = True

        col = layout.column()
        col.prop(part, "emit_from")
        col.prop(part, "use_modifier_stack")
        if part.emit_from == 'FACE' or part.emit_from == 'VOLUME':
            col.prop(part, "distribution")

        if part.emit_from == 'VERT':
            col.prop(part, "use_emit_random", text="Random Order")
        elif part.distribution == 'GRID':
            col.label(text="Grid")
            col.prop(part, "invert_grid")
            col.prop(part, "hexagonal_grid")
        else:
            col.prop(part, "use_emit_random")
            col.prop(part, "use_even_distribution")

        if part.emit_from == 'FACE' or part.emit_from == 'VOLUME':

            if part.distribution == 'JIT':
                col.prop(part, "userjit", text="Particles/Face")
                col.prop(part, "jitter_factor", text="Jittering Amount", slider=True)
            elif part.distribution == 'GRID':
                col.prop(part, "grid_resolution")
                col.prop(part, "grid_random", text="Random", slider=True)


class PARTICLE_PT_hair_dynamics(ParticleButtonsPanel, Panel):
    bl_label = "Hair Dynamics"
    bl_options = {'DEFAULT_CLOSED'}
    COMPAT_ENGINES = {'BLENDER_RENDER', 'BLENDER_CLAY', 'BLENDER_EEVEE'}

    @classmethod
    def poll(cls, context):
        psys = context.particle_system
        engine = context.engine
        if psys is None:
            return False
        if psys.settings is None:
            return False
        return psys.settings.type == 'HAIR' and (engine in cls.COMPAT_ENGINES)

    def draw_header(self, context):
        psys = context.particle_system
        self.layout.prop(psys, "use_hair_dynamics", text="")

    def draw(self, context):
        layout = self.layout

        psys = context.particle_system

        if not psys.cloth:
            return

        cloth_md = psys.cloth
        cloth = cloth_md.settings
        result = cloth_md.solver_result

        layout.enabled = psys.use_hair_dynamics and psys.point_cache.is_baked is False

        row = layout.row(align=True)
        row.menu("PARTICLE_MT_hair_dynamics_presets", text=bpy.types.PARTICLE_MT_hair_dynamics_presets.bl_label)
        row.operator("particle.hair_dynamics_preset_add", text="", icon='ZOOMIN')
        row.operator("particle.hair_dynamics_preset_add", text="", icon='ZOOMOUT').remove_active = True

        layout.use_property_split = True

        layout.separator()

        col = layout.column()
        col.label(text="Structure")
        col.prop(cloth, "mass")
        sub = col.column(align=True)
        sub.prop(cloth, "bending_stiffness", text="Stiffness")
        sub.prop(psys.settings, "bending_random", text="Random")
        col.prop(cloth, "bending_damping", text="Damping")
        # XXX has no noticeable effect with stiff hair structure springs
        #col.prop(cloth, "spring_damping", text="Damping")

        layout.separator()

        col = layout.column()
        col.label(text="Volume")
        col.prop(cloth, "air_damping", text="Air Drag")
        col.prop(cloth, "internal_friction", slider=True)

        sub = col.column(align=True)
        sub.prop(cloth, "density_target", text="Density Target")
        sub.prop(cloth, "density_strength", slider=True, text="Density Strength")
        col.prop(cloth, "voxel_cell_size")

        layout.separator()

        col = layout.column()
        col.label(text="Pinning")
        col.prop(cloth, "pin_stiffness", text="Goal Strength")

        layout.separator()

        col = layout.column()
        col.label(text="Quality")
        col.prop(cloth, "quality", text="Steps", slider=True)
        col.prop(psys.settings, "show_hair_grid", text="Display Hair Grid")

        if result:
            box = layout.box()

            if not result.status:
                label = " "
                icon = 'NONE'
            elif result.status == {'SUCCESS'}:
                label = "Success"
                icon = 'NONE'
            elif result.status - {'SUCCESS'} == {'NO_CONVERGENCE'}:
                label = "No Convergence"
                icon = 'ERROR'
            else:
                label = "ERROR"
                icon = 'ERROR'
            box.label(label, icon=icon)
            box.label("Iterations: %d .. %d (avg. %d)" %
                      (result.min_iterations, result.max_iterations, result.avg_iterations))
            box.label("Error: %.5f .. %.5f (avg. %.5f)" % (result.min_error, result.max_error, result.avg_error))


class PARTICLE_PT_cache(ParticleButtonsPanel, Panel):
    bl_label = "Cache"
    bl_options = {'DEFAULT_CLOSED'}
    COMPAT_ENGINES = {'BLENDER_RENDER', 'BLENDER_CLAY', 'BLENDER_EEVEE'}

    @classmethod
    def poll(cls, context):
        psys = context.particle_system
        engine = context.engine
        if psys is None:
            return False
        if psys.settings is None:
            return False
        if psys.settings.is_fluid:
            return False
        phystype = psys.settings.physics_type
        if phystype == 'NO' or phystype == 'KEYED':
            return False
        return (
            (psys.settings.type in {'EMITTER', 'REACTOR'} or
             (psys.settings.type == 'HAIR' and
              (psys.use_hair_dynamics or psys.point_cache.is_baked))) and
            engine in cls.COMPAT_ENGINES
        )

    def draw(self, context):
        psys = context.particle_system

        point_cache_ui(self, context, psys.point_cache, True, 'HAIR' if (psys.settings.type == 'HAIR') else 'PSYS')


class PARTICLE_PT_velocity(ParticleButtonsPanel, Panel):
    bl_label = "Velocity"
    COMPAT_ENGINES = {'BLENDER_RENDER', 'BLENDER_CLAY', 'BLENDER_EEVEE'}

    @classmethod
    def poll(cls, context):
        if particle_panel_poll(PARTICLE_PT_velocity, context):
            psys = context.particle_system
            settings = particle_get_settings(context)

            if settings.type == 'HAIR' and not settings.use_advanced_hair:
                return False
            return settings.physics_type != 'BOIDS' and (psys is None or not psys.point_cache.use_external)
        else:
            return False

    def draw(self, context):
        layout = self.layout

        psys = context.particle_system
        part = particle_get_settings(context)

        layout.enabled = particle_panel_enabled(context, psys)
        layout.use_property_split = True

        col = layout.column()
        col.label(text="Emitter Geometry")
        col.prop(part, "normal_factor")
        sub = col.column(align=True)
        sub.prop(part, "tangent_factor", text="Tangent")
        sub.prop(part, "tangent_phase", slider=True, text="Tangent Phase")

        col.separator()

        col.prop(part, "object_align_factor")

        col.label(text="Other")

        if part.emit_from == 'PARTICLE':
            col.prop(part, "particle_factor")
        else:
            col.prop(part, "object_factor", slider=True)
        col.prop(part, "factor_random")

        # if part.type=='REACTOR':
        #     sub.prop(part, "reactor_factor")
        #     sub.prop(part, "reaction_shape", slider=True)


class PARTICLE_PT_rotation(ParticleButtonsPanel, Panel):
    bl_label = "Rotation"
    bl_options = {'DEFAULT_CLOSED'}
    COMPAT_ENGINES = {'BLENDER_RENDER', 'BLENDER_CLAY', 'BLENDER_EEVEE'}

    @classmethod
    def poll(cls, context):
        if particle_panel_poll(PARTICLE_PT_rotation, context):
            psys = context.particle_system
            settings = particle_get_settings(context)

            if settings.type == 'HAIR' and not settings.use_advanced_hair:
                return False
            return settings.physics_type != 'BOIDS' and (psys is None or not psys.point_cache.use_external)
        else:
            return False

    def draw_header(self, context):
        psys = context.particle_system
        if psys:
            part = psys.settings
        else:
            part = context.space_data.pin_id

        self.layout.prop(part, "use_rotations", text="")

    def draw(self, context):
        layout = self.layout

        psys = context.particle_system
        if psys:
            part = psys.settings
        else:
            part = context.space_data.pin_id

        layout.enabled = particle_panel_enabled(context, psys) and part.use_rotations
        layout.use_property_split = True

        layout.label(text="Initial Orientation")

        col = layout.column()

        col.prop(part, "rotation_mode")
        col.prop(part, "rotation_factor_random", slider=True, text="Randomize")

        col.separator()

        col.prop(part, "phase_factor", slider=True)
        col.prop(part, "phase_factor_random", text="Randomize Phase ", slider=True)

        if part.type != 'HAIR':
            col.prop(part, "use_dynamic_rotation")

            col.separator()

            col.label(text="Angular Velocity")

            col.prop(part, "angular_velocity_mode", text="Axis")
            sub = col.column(align=True)
            sub.active = part.angular_velocity_mode != 'NONE'
            sub.prop(part, "angular_velocity_factor", text="Amount")


class PARTICLE_PT_physics(ParticleButtonsPanel, Panel):
    bl_label = "Physics"
    COMPAT_ENGINES = {'BLENDER_RENDER', 'BLENDER_CLAY', 'BLENDER_EEVEE'}

    @classmethod
    def poll(cls, context):
        if particle_panel_poll(PARTICLE_PT_physics, context):
            psys = context.particle_system
            settings = particle_get_settings(context)

            if settings.type == 'HAIR' and not settings.use_advanced_hair:
                return False
            return psys is None or not psys.point_cache.use_external
        else:
            return False

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True

        psys = context.particle_system
        part = particle_get_settings(context)

        layout.enabled = particle_panel_enabled(context, psys)

        layout.prop(part, "physics_type")

        col = layout.column()
        if part.physics_type != 'NO':
            col = col.column()
            col.prop(part, "mass")
            col.prop(part, "use_multiply_size_mass", text="Multiply mass with size")

        if part.physics_type in {'NEWTON', 'FLUID'}:

            col.prop(part, "use_size_deflect")
            col.prop(part, "use_die_on_collision")

            col.prop(part, "collision_group")

            col.label(text="Forces")
            col.prop(part, "brownian_factor")
            col.prop(part, "drag_factor", slider=True)
            col.prop(part, "damping", slider=True)

            col.label(text="Integration")
            col.prop(part, "integrator")
            col.prop(part, "timestep")
            sub = col.row()
            sub.prop(part, "subframes")
            supports_courant = part.physics_type == 'FLUID'
            subsub = sub.row()
            subsub.enabled = supports_courant
            subsub.prop(part, "use_adaptive_subframes", text="")
            if supports_courant and part.use_adaptive_subframes:
                col.prop(part, "courant_target", text="Threshold")

            if part.physics_type == 'FLUID':
                fluid = part.fluid

                col.label(text="Fluid")
                col.prop(fluid, "solver")
                col.prop(fluid, "stiffness", text="Stiffness")
                col.prop(fluid, "linear_viscosity", text="Viscosity")
                col.prop(fluid, "buoyancy", text="Buoyancy", slider=True)

                col.label(text="Advanced")

                if fluid.solver == 'DDR':
                    sub = col.column()
                    sub.prop(fluid, "repulsion", slider=fluid.factor_repulsion)
                    sub.prop(fluid, "factor_repulsion")

                    sub.prop(fluid, "stiff_viscosity", slider=fluid.factor_stiff_viscosity)
                    sub.prop(fluid, "factor_stiff_viscosity")

                sub = col.column()
                sub.prop(fluid, "fluid_radius", slider=fluid.factor_radius)
                sub.prop(fluid, "factor_radius")

                sub.prop(fluid, "rest_density", slider=fluid.use_factor_density)
                sub.prop(fluid, "use_factor_density")

                if fluid.solver == 'CLASSICAL':
                    # With the classical solver, it is possible to calculate the
                    # spacing between particles when the fluid is at rest. This
                    # makes it easier to set stable initial conditions.
                    particle_volume = part.mass / fluid.rest_density
                    spacing = pow(particle_volume, 1.0 / 3.0)

                    sub.label(text="Spacing: %g" % spacing)

                elif fluid.solver == 'DDR':

                    col.label(text="Springs")
                    col.prop(fluid, "spring_force", text="Force")
                    col.prop(fluid, "use_viscoelastic_springs")

                    sub = col.column()
                    sub.active = fluid.use_viscoelastic_springs
                    sub.prop(fluid, "yield_ratio", slider=True)
                    sub.prop(fluid, "plasticity", slider=True)

                    col.label(text="Advanced")
                    sub = col.column()
                    sub.prop(fluid, "rest_length", slider=fluid.factor_rest_length)
                    sub.prop(fluid, "factor_rest_length", text="")

                    sub = col.column()
                    sub.active = fluid.use_viscoelastic_springs
                    sub.prop(fluid, "use_initial_rest_length")
                    sub.prop(fluid, "spring_frames", text="Frames")

        elif part.physics_type == 'KEYED':

            sub = col.column()
            sub.active = not psys.use_keyed_timing
            sub.prop(part, "keyed_loops", text="Loops")
            if psys:
                col.prop(psys, "use_keyed_timing", text="Use Timing")

            col.label(text="Keys")

        elif part.physics_type == 'BOIDS':
            boids = part.boids

            row = layout.row()
            row.prop(boids, "use_flight")
            row.prop(boids, "use_land")
            row.prop(boids, "use_climb")

            split = layout.split()

            col = split.column(align=True)
            col.active = boids.use_flight
            col.prop(boids, "air_speed_max")
            col.prop(boids, "air_speed_min", slider=True)
            col.prop(boids, "air_acc_max", slider=True)
            col.prop(boids, "air_ave_max", slider=True)
            col.prop(boids, "air_personal_space")
            row = col.row(align=True)
            row.active = (boids.use_land or boids.use_climb) and boids.use_flight
            row.prop(boids, "land_smooth")

            col = split.column(align=True)
            col.active = boids.use_land or boids.use_climb
            col.prop(boids, "land_speed_max")
            col.prop(boids, "land_jump_speed")
            col.prop(boids, "land_acc_max", slider=True)
            col.prop(boids, "land_ave_max", slider=True)
            col.prop(boids, "land_personal_space")
            col.prop(boids, "land_stick_force")

            layout.prop(part, "collision_group")

            split = layout.split()

            col = split.column(align=True)
            col.label(text="Battle:")
            col.prop(boids, "health")
            col.prop(boids, "strength")
            col.prop(boids, "aggression")
            col.prop(boids, "accuracy")
            col.prop(boids, "range")

            col = split.column()
            col.label(text="Misc:")
            col.prop(boids, "bank", slider=True)
            col.prop(boids, "pitch", slider=True)
            col.prop(boids, "height", slider=True)

        if psys and part.physics_type in {'KEYED', 'BOIDS', 'FLUID'}:
            if part.physics_type == 'BOIDS':
                layout.label(text="Relations:")
            elif part.physics_type == 'FLUID':
                layout.label(text="Fluid Interaction:")

            row = layout.row()
            row.template_list("UI_UL_list", "particle_targets", psys, "targets",
                              psys, "active_particle_target_index", rows=4)

            col = row.column()
            sub = col.row()
            subsub = sub.column(align=True)
            subsub.operator("particle.new_target", icon='ZOOMIN', text="")
            subsub.operator("particle.target_remove", icon='ZOOMOUT', text="")
            sub = col.row()
            subsub = sub.column(align=True)
            subsub.operator("particle.target_move_up", icon='TRIA_UP', text="")
            subsub.operator("particle.target_move_down", icon='TRIA_DOWN', text="")

            key = psys.active_particle_target
            if key:
                row = layout.row()
                if part.physics_type == 'KEYED':
                    col = row.column()
                    # doesn't work yet
                    #col.alert = key.valid
                    col.prop(key, "object", text="")
                    col.prop(key, "system", text="System")
                    col = row.column()
                    col.active = psys.use_keyed_timing
                    col.prop(key, "time")
                    col.prop(key, "duration")
                elif part.physics_type == 'BOIDS':
                    sub = row.row()
                    # doesn't work yet
                    #sub.alert = key.valid
                    sub.prop(key, "object", text="")
                    sub.prop(key, "system", text="System")

                    layout.row().prop(key, "alliance", expand=True)
                elif part.physics_type == 'FLUID':
                    sub = row.row()
                    # doesn't work yet
                    #sub.alert = key.valid
                    sub.prop(key, "object", text="")
                    sub.prop(key, "system", text="System")


class PARTICLE_PT_boidbrain(ParticleButtonsPanel, Panel):
    bl_label = "Boid Brain"
    COMPAT_ENGINES = {'BLENDER_RENDER', 'BLENDER_CLAY', 'BLENDER_EEVEE'}

    @classmethod
    def poll(cls, context):
        psys = context.particle_system
        settings = particle_get_settings(context)
        engine = context.engine

        if settings is None:
            return False
        if psys is not None and psys.point_cache.use_external:
            return False
        return settings.physics_type == 'BOIDS' and engine in cls.COMPAT_ENGINES

    def draw(self, context):
        layout = self.layout

        boids = particle_get_settings(context).boids

        layout.enabled = particle_panel_enabled(context, context.particle_system)

        # Currently boids can only use the first state so these are commented out for now.
        #row = layout.row()
        #row.template_list("UI_UL_list", "particle_boids", boids, "states",
        #                  boids, "active_boid_state_index", compact="True")
        #col = row.row()
        #sub = col.row(align=True)
        #sub.operator("boid.state_add", icon='ZOOMIN', text="")
        #sub.operator("boid.state_del", icon='ZOOMOUT', text="")
        #sub = row.row(align=True)
        #sub.operator("boid.state_move_up", icon='TRIA_UP', text="")
        #sub.operator("boid.state_move_down", icon='TRIA_DOWN', text="")

        state = boids.active_boid_state

        #layout.prop(state, "name", text="State name")

        row = layout.row()
        row.prop(state, "ruleset_type")
        if state.ruleset_type == 'FUZZY':
            row.prop(state, "rule_fuzzy", slider=True)
        else:
            row.label(text="")

        row = layout.row()
        row.template_list("UI_UL_list", "particle_boids_rules", state,
                          "rules", state, "active_boid_rule_index", rows=4)

        col = row.column()
        sub = col.row()
        subsub = sub.column(align=True)
        subsub.operator_menu_enum("boid.rule_add", "type", icon='ZOOMIN', text="")
        subsub.operator("boid.rule_del", icon='ZOOMOUT', text="")
        sub = col.row()
        subsub = sub.column(align=True)
        subsub.operator("boid.rule_move_up", icon='TRIA_UP', text="")
        subsub.operator("boid.rule_move_down", icon='TRIA_DOWN', text="")

        rule = state.active_boid_rule

        if rule:
            row = layout.row()
            row.prop(rule, "name", text="")
            # somebody make nice icons for boids here please! -jahka
            row.prop(rule, "use_in_air", icon='TRIA_UP', text="")
            row.prop(rule, "use_on_land", icon='TRIA_DOWN', text="")

            row = layout.row()

            if rule.type == 'GOAL':
                row.prop(rule, "object")
                row = layout.row()
                row.prop(rule, "use_predict")
            elif rule.type == 'AVOID':
                row.prop(rule, "object")
                row = layout.row()
                row.prop(rule, "use_predict")
                row.prop(rule, "fear_factor")
            elif rule.type == 'FOLLOW_PATH':
                row.label(text="Not yet functional")
            elif rule.type == 'AVOID_COLLISION':
                row.prop(rule, "use_avoid")
                row.prop(rule, "use_avoid_collision")
                row.prop(rule, "look_ahead")
            elif rule.type == 'FOLLOW_LEADER':
                row.prop(rule, "object", text="")
                row.prop(rule, "distance")
                row = layout.row()
                row.prop(rule, "use_line")
                sub = row.row()
                sub.active = rule.line
                sub.prop(rule, "queue_count")
            elif rule.type == 'AVERAGE_SPEED':
                row.prop(rule, "speed", slider=True)
                row.prop(rule, "wander", slider=True)
                row.prop(rule, "level", slider=True)
            elif rule.type == 'FIGHT':
                row.prop(rule, "distance")
                row.prop(rule, "flee_distance")


class PARTICLE_PT_render(ParticleButtonsPanel, Panel):
    bl_label = "Render"
    COMPAT_ENGINES = {'BLENDER_RENDER', 'BLENDER_CLAY', 'BLENDER_EEVEE'}

    @classmethod
    def poll(cls, context):
        settings = particle_get_settings(context)
        engine = context.engine
        if settings is None:
            return False

        return engine in cls.COMPAT_ENGINES

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True

        psys = context.particle_system
        part = particle_get_settings(context)

        layout.prop(part, "render_type", text="Render As")

        if part.type == 'EMITTER' or \
           (part.render_type in {'OBJECT', 'GROUP'} and part.type == 'HAIR'):
            if part.render_type not in {'NONE'}:

                col = layout.column(align=True)
                col.prop(part, "particle_size", text="Scale")
                col.prop(part, "size_random", slider=True, text="Scale Randomness")

        if psys:
            col = layout.column()
            if part.render_type not in {'OBJECT', 'GROUP', 'NONE'}:
                # col.enabled = False
                col.prop(part, "material_slot", text="Material")
                col.prop(psys, "parent", text="Coordinate System")

        if part.render_type not in {'NONE'}:
            col = layout.column()
            col.prop(part, "use_parent_particles", text="Parent Particles")
            col.prop(part, "show_unborn", text="Unborn")
            col.prop(part, "use_dead", text="Dead")

        col = layout.column()

        if part.render_type == 'LINE':
            col.separator()
            col.label(text="Line")
            sub = col.column(align=True)
            sub.prop(part, "line_length_tail", text="Length Tail")
            sub.prop(part, "line_length_head", text="Head")

            col.prop(part, "use_velocity_length", text="Velocity Length")
        elif part.render_type == 'PATH':
            col.separator()
            col.label(text="Path")
            col.prop(part, "use_strand_primitive")
            sub = col.column()
            sub.active = (part.use_strand_primitive is False)
            sub.prop(part, "use_render_adaptive")
            sub = col.column()
            sub.active = part.use_render_adaptive or part.use_strand_primitive is True
            sub.prop(part, "adaptive_angle")
            sub = col.column()
            sub.active = (part.use_render_adaptive is True and part.use_strand_primitive is False)
            sub.prop(part, "adaptive_pixel")
            col.prop(part, "use_hair_bspline")
            col.prop(part, "render_step", text="Steps")

            col.separator()

            col.label(text="Timing")
            col.prop(part, "use_absolute_path_time")

            if part.type == 'HAIR' or psys.point_cache.is_baked:
                col.prop(part, "path_start", text="Start", slider=not part.use_absolute_path_time)
            else:
                col.prop(part, "trail_count")

            col.prop(part, "path_end", text="End", slider=not part.use_absolute_path_time)
            col.prop(part, "length_random", text="Random", slider=True)

        elif part.render_type == 'OBJECT':
            col.separator()

            col.label(text="Object")

            col.prop(part, "dupli_object", text="Instance Object")
            sub = col.column()
            sub.prop(part, "use_global_dupli", text="Global Coordinates")
            sub.prop(part, "use_rotation_dupli", text="Object Rotation")
            sub.prop(part, "use_scale_dupli", text="Object Scale")
        elif part.render_type == 'GROUP':
            col.separator()

            col.label(text="Group")

            col.prop(part, "dupli_group")

            col.prop(part, "use_whole_group")
            sub = col.column()
            sub.active = (part.use_whole_group is False)
            sub.prop(part, "use_group_pick_random")
            sub.prop(part, "use_global_dupli", text="Global Coordinates")
            sub.prop(part, "use_rotation_dupli", text="Object Rotation")
            sub.prop(part, "use_scale_dupli", text="Object Scale")
            sub.prop(part, "use_group_count")

            if part.use_group_count and not part.use_whole_group:
                row = layout.row()
                row.template_list("UI_UL_list", "particle_dupli_weights", part, "dupli_weights",
                                  part, "active_dupliweight_index")

                col = row.column()
                sub = col.row()
                subsub = sub.column(align=True)
                subsub.operator("particle.dupliob_copy", icon='ZOOMIN', text="")
                subsub.operator("particle.dupliob_remove", icon='ZOOMOUT', text="")
                subsub.operator("particle.dupliob_move_up", icon='TRIA_UP', text="")
                subsub.operator("particle.dupliob_move_down", icon='TRIA_DOWN', text="")

                weight = part.active_dupliweight
                if weight:
                    row = layout.row()
                    row.prop(weight, "count")

        elif part.render_type == 'BILLBOARD':

            ob = context.object

            col.separator()

            col.label(text="Alignment")
            col.prop(part, "billboard_align", text="Align To")
            col.prop(part, "lock_billboard", text="Lock Axis")
            col.prop(part, "billboard_object")

            col.separator()
            col.label(text="Tilt")

            sub = col.column(align=True)
            sub.prop(part, "billboard_tilt", text="Angle", slider=True)
            sub.prop(part, "billboard_tilt_random", text="Random", slider=True)

            sub = col.column(align=True)
            sub.prop(part, "billboard_offset")
            col.prop(part, "billboard_size", text="Scale")
            if part.billboard_align == 'VEL':
                col = col.column(align=True)
                col.prop(part, "billboard_velocity_head", text="Velocity ScaleHead")
                col.prop(part, "billboard_velocity_tail", text="Tail")

            col.separator()
            col.label(text="UVs")

            if psys:
                col.prop_search(psys, "billboard_normal_uv", ob.data, "uv_layers")
                col.prop_search(psys, "billboard_time_index_uv", ob.data, "uv_layers")

            col.prop(part, "billboard_uv_split", text="Split UVs")

            if psys:
                sub = col.column()
                sub.active = part.billboard_uv_split > 1
                sub.prop_search(psys, "billboard_split_uv", ob.data, "uv_layers")

            sub.prop(part, "billboard_animation")
            sub.prop(part, "billboard_offset_split")

        if part.render_type == 'HALO' or part.render_type == 'LINE' or part.render_type == 'BILLBOARD':

            col.separator()

            col.label(text="Trails")

            col.prop(part, "trail_count")

            sub = col.column()
            sub.active = (part.trail_count > 1)
            sub.prop(part, "use_absolute_path_time", text="Length in Frames")
            sub.prop(part, "path_end", text="Length", slider=not part.use_absolute_path_time)
            sub.prop(part, "length_random", text="Random Length", slider=True)


class PARTICLE_PT_draw(ParticleButtonsPanel, Panel):
    bl_label = "Viewport Display"
    bl_options = {'DEFAULT_CLOSED'}
    COMPAT_ENGINES = {'BLENDER_RENDER', 'BLENDER_CLAY', 'BLENDER_EEVEE'}

    @classmethod
    def poll(cls, context):
        settings = particle_get_settings(context)
        engine = context.engine
        if settings is None:
            return False
        return engine in cls.COMPAT_ENGINES

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True

        psys = context.particle_system
        part = particle_get_settings(context)

        layout.prop(part, "draw_method", text="Display As")

        if part.draw_method == 'NONE' or (part.render_type == 'NONE' and part.draw_method == 'RENDER'):
            return

        path = (part.render_type == 'PATH' and part.draw_method == 'RENDER') or part.draw_method == 'PATH'

        layout.separator()

        col = layout.column()
        col.prop(part, "draw_color", text="Color")
        if part.draw_color in {'VELOCITY', 'ACCELERATION'}:
            col.prop(part, "color_maximum", text="Fade Distance")

        col = layout.column()

        if path:
            col.prop(part, "draw_step", text="Strand Steps")
        col.prop(part, "draw_percentage", slider=True, text="Amount")
        if part.draw_method != 'RENDER' or part.render_type == 'HALO':
            col.prop(part, "draw_size", text="Size")

        if part.draw_percentage != 100 and psys is not None:
            if part.type == 'HAIR':
                if psys.use_hair_dynamics and psys.point_cache.is_baked is False:
                    layout.row().label(text="Display percentage makes dynamics inaccurate without baking")
            else:
                phystype = part.physics_type
                if phystype != 'NO' and phystype != 'KEYED' and psys.point_cache.is_baked is False:
                    layout.row().label(text="Display percentage makes dynamics inaccurate without baking")
        else:
            layout.row().label(text="")

        col = layout.column()
        col.prop(part, "show_guide_hairs", text="Guide Hairs")
        col.prop(part, "show_size")
        col.prop(part, "show_velocity")
        col.prop(part, "show_number")
        if part.physics_type == 'BOIDS':
            col.prop(part, "show_health")


class PARTICLE_PT_children(ParticleButtonsPanel, Panel):
    bl_label = "Children"
    bl_options = {'DEFAULT_CLOSED'}
    COMPAT_ENGINES = {'BLENDER_RENDER', 'BLENDER_CLAY', 'BLENDER_EEVEE'}

    @classmethod
    def poll(cls, context):
        return particle_panel_poll(cls, context)

    def draw(self, context):
        layout = self.layout

        psys = context.particle_system
        part = particle_get_settings(context)

        layout.row().prop(part, "child_type", expand=True)

        layout.use_property_split = True

        if part.child_type == 'NONE':
            return

        col = layout.column()

        sub = col.column(align=True)
        sub.prop(part, "child_nbr", text="Display Amount")
        sub.prop(part, "rendered_child_count", text="Render Amount")

        col.separator()

        col.prop(part, "child_length", slider=True)
        col.prop(part, "child_length_threshold", slider=True)
        if psys:
            col.prop(psys, "child_seed", text="Seed")

        col.separator()

        if part.child_type == 'INTERPOLATED':
            col.prop(part, "virtual_parents", slider=True)
            col.prop(part, "create_long_hair_children")
        else:
            col.separator()
            sub = col.column(align=True)
            sub.prop(part, "child_size", text="Size")
            sub.prop(part, "child_size_random", text="Randomize Size", slider=True)

        if part.child_type == 'SIMPLE':
            col.separator()
            col.prop(part, "child_radius", text="Radius")
            col.prop(part, "child_roundness", text="Roundness", slider=True)
        elif part.virtual_parents > 0.0:
            sub = col.column(align=True)
            sub.label(text="Parting not available with virtual parents")
        else:
            col.separator()
            col.label(text="Parting")
            sub = col.column(align=True)
            sub.prop(part, "child_parting_factor", text="Parting", slider=True)
            sub.prop(part, "child_parting_min", text="Min")
            sub.prop(part, "child_parting_max", text="Max")

        col.separator()

        col.label(text="Clumping")

        sub = col.column()
        if part.child_type == 'SIMPLE':
            sub.prop(part, "twist")
            sub.prop(part, "use_twist_curve")
            if part.use_twist_curve:
                sub.template_curve_mapping(part, "twist_curve")

        sub.prop(part, "use_clump_curve")
        if part.use_clump_curve:
            sub.template_curve_mapping(part, "clump_curve")
        else:
            sub.prop(part, "clump_factor", slider=True)
            sub.prop(part, "clump_shape", slider=True)
        sub = col.column(align=True)
        sub.prop(part, "use_clump_noise")
        subsub = sub.column()
        subsub.enabled = part.use_clump_noise
        subsub.prop(part, "clump_noise_size")

        col.label(text="Roughness")

        col.prop(part, "use_roughness_curve")
        if part.use_roughness_curve:
            sub = col.column()
            sub.template_curve_mapping(part, "roughness_curve")
            sub.prop(part, "roughness_1", text="Roughness")
            sub.prop(part, "roughness_1_size", text="Size")
        else:
            sub = col.column(align=True)
            sub.prop(part, "roughness_1", text="Uniform")
            sub.prop(part, "roughness_1_size", text="Size")

            sub = col.column(align=True)
            sub.prop(part, "roughness_endpoint", "Endpoint")
            sub.prop(part, "roughness_end_shape")

            sub = col.column(align=True)
            sub.prop(part, "roughness_2", text="Random")
            sub.prop(part, "roughness_2_size", text="Size")
            sub.prop(part, "roughness_2_threshold", slider=True)

        col.label(text="Kink")

        col.prop(part, "kink", text="Kink Type")
        col = layout.column()
        col.active = part.kink != 'NO'

        if part.kink == 'SPIRAL':

            sub = col.column()
            sub.prop(part, "kink_amplitude", text="Amplitude")
            sub.prop(part, "kink_amplitude_random", text="Randomize Amplitude", slider=True)

            col.separator()

            sub = col.column()
            sub.prop(part, "kink_axis")
            sub.prop(part, "kink_axis_random", text="Randomize Axis", slider=True)

            col.separator()

            col.prop(part, "kink_frequency", text="Frequency")
            col.prop(part, "kink_shape", text="Shape", slider=True)
            col.prop(part, "kink_extra_steps", text="Steps")

        elif part.kink in {'CURL', 'RADIAL', 'WAVE', 'BRAID', 'WAVE'}:
            sub = col.column(align=True)
            sub.prop(part, "kink_amplitude")
            sub.prop(part, "kink_amplitude_clump", text="Clump", slider=True)
            col.prop(part, "kink_flat", slider=True)
            col.prop(part, "kink_frequency")
            col.prop(part, "kink_shape", slider=True)


class PARTICLE_PT_field_weights(ParticleButtonsPanel, Panel):
    bl_label = "Field Weights"
    bl_options = {'DEFAULT_CLOSED'}
    COMPAT_ENGINES = {'BLENDER_RENDER', 'BLENDER_CLAY', 'BLENDER_EEVEE'}

    @classmethod
    def poll(cls, context):
        return particle_panel_poll(cls, context)

    def draw(self, context):
        part = particle_get_settings(context)
        effector_weights_ui(self, context, part.effector_weights, 'PSYS')

        if part.type == 'HAIR':
            row = self.layout.row()
            row.prop(part.effector_weights, "apply_to_hair_growing")
            row.prop(part, "apply_effector_to_children")
            row = self.layout.row()
            row.prop(part, "effect_hair", slider=True)


class PARTICLE_PT_force_fields(ParticleButtonsPanel, Panel):
    bl_label = "Force Field Settings"
    bl_options = {'DEFAULT_CLOSED'}
    COMPAT_ENGINES = {'BLENDER_RENDER', 'BLENDER_CLAY', 'BLENDER_EEVEE'}

    def draw(self, context):
        layout = self.layout

        part = particle_get_settings(context)

        row = layout.row()
        row.prop(part, "use_self_effect")
        row.prop(part, "effector_amount", text="Amount")

        split = layout.split(percentage=0.2)
        split.label(text="Type 1:")
        split.prop(part.force_field_1, "type", text="")
        basic_force_field_settings_ui(self, context, part.force_field_1)
        if part.force_field_1.type != 'NONE':
            layout.label(text="Falloff:")
        basic_force_field_falloff_ui(self, context, part.force_field_1)

        if part.force_field_1.type != 'NONE':
            layout.label(text="")

        split = layout.split(percentage=0.2)
        split.label(text="Type 2:")
        split.prop(part.force_field_2, "type", text="")
        basic_force_field_settings_ui(self, context, part.force_field_2)
        if part.force_field_2.type != 'NONE':
            layout.label(text="Falloff:")
        basic_force_field_falloff_ui(self, context, part.force_field_2)


class PARTICLE_PT_vertexgroups(ParticleButtonsPanel, Panel):
    bl_label = "Vertex Groups"
    bl_options = {'DEFAULT_CLOSED'}
    COMPAT_ENGINES = {'BLENDER_RENDER', 'BLENDER_CLAY', 'BLENDER_EEVEE'}

    @classmethod
    def poll(cls, context):
        if context.particle_system is None:
            return False
        return particle_panel_poll(cls, context)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True

        ob = context.object
        psys = context.particle_system

        col = layout.column()
        row = col.row(align=True)
        row.prop_search(psys, "vertex_group_density", ob, "vertex_groups", text="Density")
        row.prop(psys, "invert_vertex_group_density", text="", toggle=True, icon='ARROW_LEFTRIGHT')

        row = col.row(align=True)
        row.prop_search(psys, "vertex_group_length", ob, "vertex_groups", text="Length")
        row.prop(psys, "invert_vertex_group_length", text="", toggle=True, icon='ARROW_LEFTRIGHT')

        row = col.row(align=True)
        row.prop_search(psys, "vertex_group_clump", ob, "vertex_groups", text="Clump")
        row.prop(psys, "invert_vertex_group_clump", text="", toggle=True, icon='ARROW_LEFTRIGHT')

        row = col.row(align=True)
        row.prop_search(psys, "vertex_group_kink", ob, "vertex_groups", text="Kink")
        row.prop(psys, "invert_vertex_group_kink", text="", toggle=True, icon='ARROW_LEFTRIGHT')

        row = col.row(align=True)
        row.prop_search(psys, "vertex_group_roughness_1", ob, "vertex_groups", text="Roughness 1")
        row.prop(psys, "invert_vertex_group_roughness_1", text="", toggle=True, icon='ARROW_LEFTRIGHT')

        row = col.row(align=True)
        row.prop_search(psys, "vertex_group_roughness_2", ob, "vertex_groups", text="Roughness 2")
        row.prop(psys, "invert_vertex_group_roughness_2", text="", toggle=True, icon='ARROW_LEFTRIGHT')

        row = col.row(align=True)
        row.prop_search(psys, "vertex_group_roughness_end", ob, "vertex_groups", text="Roughness End")
        row.prop(psys, "invert_vertex_group_roughness_end", text="", toggle=True, icon='ARROW_LEFTRIGHT')

        row = col.row(align=True)
        row.prop_search(psys, "vertex_group_twist", ob, "vertex_groups", text="Twist")
        row.prop(psys, "invert_vertex_group_twist", text="", toggle=True, icon='ARROW_LEFTRIGHT')

        # Commented out vertex groups don't work and are still waiting for better implementation
        # row = layout.row()
        # row.prop_search(psys, "vertex_group_velocity", ob, "vertex_groups", text="Velocity")
        # row.prop(psys, "invert_vertex_group_velocity", text="")

        # row = layout.row()
        # row.prop_search(psys, "vertex_group_size", ob, "vertex_groups", text="Size")
        # row.prop(psys, "invert_vertex_group_size", text="")

        # row = layout.row()
        # row.prop_search(psys, "vertex_group_tangent", ob, "vertex_groups", text="Tangent")
        # row.prop(psys, "invert_vertex_group_tangent", text="")

        # row = layout.row()
        # row.prop_search(psys, "vertex_group_rotation", ob, "vertex_groups", text="Rotation")
        # row.prop(psys, "invert_vertex_group_rotation", text="")

        # row = layout.row()
        # row.prop_search(psys, "vertex_group_field", ob, "vertex_groups", text="Field")
        # row.prop(psys, "invert_vertex_group_field", text="")


class PARTICLE_PT_textures(ParticleButtonsPanel, Panel):
    bl_label = "Textures"
    bl_options = {'DEFAULT_CLOSED'}
    COMPAT_ENGINES = {'BLENDER_RENDER', 'BLENDER_CLAY', 'BLENDER_EEVEE'}

    @classmethod
    def poll(cls, context):
        if context.particle_system is None:
            return False
        return particle_panel_poll(cls, context)

    def draw(self, context):
        layout = self.layout

        psys = context.particle_system
        part = psys.settings

        row = layout.row()
        row.template_list("TEXTURE_UL_texslots", "", part, "texture_slots", part, "active_texture_index", rows=2)

        col = row.column(align=True)
        col.operator("texture.slot_move", text="", icon='TRIA_UP').type = 'UP'
        col.operator("texture.slot_move", text="", icon='TRIA_DOWN').type = 'DOWN'
        col.menu("TEXTURE_MT_specials", icon='DOWNARROW_HLT', text="")

        if not part.active_texture:
            layout.template_ID(part, "active_texture", new="texture.new")
        else:
            slot = part.texture_slots[part.active_texture_index]
            layout.template_ID(slot, "texture", new="texture.new")


class PARTICLE_PT_hair_shape(ParticleButtonsPanel, Panel):
    bl_label = "Hair Shape"
    bl_options = {'DEFAULT_CLOSED'}
    COMPAT_ENGINES = {'BLENDER_RENDER', 'BLENDER_CLAY', 'BLENDER_EEVEE'}

    @classmethod
    def poll(cls, context):
        if context.particle_system is None:
            return False
        return particle_panel_poll(cls, context)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True

        psys = context.particle_system
        part = psys.settings

        layout.prop(part, "shape", text="Strand Shape")

        col = layout.column(align=True)
        col.prop(part, "root_radius", text="Radius Root")
        col.prop(part, "tip_radius", text="Tip")

        col = layout.column()
        col.prop(part, "radius_scale", text="Radius Scaling")
        col.prop(part, "use_close_tip")


class PARTICLE_PT_custom_props(ParticleButtonsPanel, PropertyPanel, Panel):
    COMPAT_ENGINES = {'BLENDER_RENDER', 'BLENDER_CLAY', 'BLENDER_EEVEE'}
    _context_path = "particle_system.settings"
    _property_type = bpy.types.ParticleSettings


classes = (
    PARTICLE_MT_specials,
    PARTICLE_MT_hair_dynamics_presets,
    PARTICLE_UL_particle_systems,
    PARTICLE_PT_context_particles,
    PARTICLE_PT_emission,
    PARTICLE_PT_emission_source,
    PARTICLE_PT_hair_dynamics,
    PARTICLE_PT_cache,
    PARTICLE_PT_velocity,
    PARTICLE_PT_rotation,
    PARTICLE_PT_physics,
    PARTICLE_PT_boidbrain,
    PARTICLE_PT_render,
    PARTICLE_PT_draw,
    PARTICLE_PT_children,
    PARTICLE_PT_hair_shape,
    PARTICLE_PT_field_weights,
    PARTICLE_PT_force_fields,
    PARTICLE_PT_vertexgroups,
    PARTICLE_PT_textures,
    PARTICLE_PT_custom_props,
)

if __name__ == "__main__":  # only for live edit.
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)
