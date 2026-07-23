"""Full-screen bloom post-processing.

A small, custom GPU bloom pass -- bright-pass extract, then a
separable horizontal+vertical blur, then an additive combine with the
untouched original frame -- run once over the entire finished frame.
This is what lighting.py's point lights can't do alone: any
sufficiently bright pixel (a laser core, an explosion, a fully-lit
patch of starfield) now bleeds a soft halo into its dark surroundings,
instead of staying confined to each light's own falloff radius.

Built by hand with arcade.experimental.Shadertoy/ShadertoyBuffer
rather than arcade's bundled experimental.bloom_filter.BloomFilter:
that one's final combine pass never actually samples the original
frame (its own buffer_a is both the "base" and the bloom source), so
setting its intensity to 0 blacks out the entire screen instead of
just removing the glow -- not a usable "add bloom on top" filter as
shipped. This version keeps the base frame completely untouched
wherever nothing is bright enough to bloom.

HUD/menu text is deliberately drawn AFTER this pass, straight onto the
window, so bloom never affects text legibility -- the same rule
lighting.py already follows for the same reason.
"""

from arcade.experimental.shadertoy import Shadertoy, ShadertoyBuffer

# Pixels dimmer than this (0-1 luma-ish, actually max channel) don't
# bloom at all; the deep-navy starfield background sits well under
# this so it stays untouched. Raise it if faint things start glowing
# that shouldn't; lower it if bright sprites aren't blooming enough.
THRESHOLD = 0.65

# How much the bright-pass result is boosted before blurring. Higher
# = a more intense/wider-reaching glow off the same bright pixels.
INTENSITY = 1.4

# How far (in texels, before the *3 spread baked into the shader) the
# blur reaches. Bigger = softer, wider-reaching halo; smaller = a
# tighter glow that hugs the light source more closely.
BLUR_RADIUS = 4

_BRIGHT_PASS_SOURCE = """
uniform float threshold;
uniform float intensity;

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = fragCoord / iResolution.xy;
    vec3 color = texture(iChannel0, uv).rgb;
    float brightness = max(color.r, max(color.g, color.b));
    float contribution = smoothstep(threshold, threshold + 0.25, brightness);
    fragColor = vec4(color * contribution * intensity, 1.0);
}
"""

_BLUR_WEIGHTS = "float[9](0.05, 0.09, 0.12, 0.15, 0.18, 0.15, 0.12, 0.09, 0.05)"

_HBLUR_SOURCE = f"""
void mainImage(out vec4 fragColor, in vec2 fragCoord) {{
    vec2 uv = fragCoord / iResolution.xy;
    vec2 texel = 1.0 / iResolution.xy;
    float weights[9] = {_BLUR_WEIGHTS};
    vec3 sum = vec3(0.0);
    for (int i = -4; i <= 4; i++) {{
        sum += texture(iChannel0,
            uv + vec2(float(i) * texel.x * 3.0, 0.0)).rgb * weights[i + 4];
    }}
    fragColor = vec4(sum, 1.0);
}}
"""

_VBLUR_SOURCE = f"""
void mainImage(out vec4 fragColor, in vec2 fragCoord) {{
    vec2 uv = fragCoord / iResolution.xy;
    vec2 texel = 1.0 / iResolution.xy;
    float weights[9] = {_BLUR_WEIGHTS};
    vec3 sum = vec3(0.0);
    for (int i = -4; i <= 4; i++) {{
        sum += texture(iChannel0,
            uv + vec2(0.0, float(i) * texel.y * 3.0)).rgb * weights[i + 4];
    }}
    fragColor = vec4(sum, 1.0);
}}
"""

_COMBINE_SOURCE = """
void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = fragCoord / iResolution.xy;
    vec3 base = texture(iChannel0, uv).rgb;
    vec3 bloom = texture(iChannel1, uv).rgb;
    fragColor = vec4(base + bloom, 1.0);
}
"""

# Never actually rendered with its own shader -- this buffer exists
# purely as a plain render target the game draws straight into (via
# .fbo.use()/.clear()), so its own "source" is an unused passthrough.
_PASSTHROUGH_SOURCE = """
void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    fragColor = texture(iChannel0, fragCoord / iResolution.xy);
}
"""


class PostFX:
    """Owns the offscreen framebuffer the whole lit scene renders into,
    and the bloom shader chain that turns it into the final frame.

    Usage from AlienInvasion.on_draw:
        self.post_fx.use()
        self.post_fx.clear()
        <draw everything that should be affected by bloom>
        self.use()             # rebind the real window
        self.post_fx.draw()
        <draw HUD, unaffected by bloom, straight onto the window>
    """

    def __init__(self, width, height, threshold=THRESHOLD,
            intensity=INTENSITY):
        size = (width, height)

        # The scene renders into this -- its own texture doubles as
        # both "the original frame" (final combine's channel_0) and
        # the bright-pass's input.
        self._scene = ShadertoyBuffer(size, _PASSTHROUGH_SOURCE)

        self._bright_pass = ShadertoyBuffer(size, _BRIGHT_PASS_SOURCE)
        self._bright_pass.program["threshold"] = threshold
        self._bright_pass.program["intensity"] = intensity
        self._bright_pass.channel_0 = self._scene.texture

        self._hblur = ShadertoyBuffer(size, _HBLUR_SOURCE)
        self._hblur.channel_0 = self._bright_pass.texture

        self._vblur = ShadertoyBuffer(size, _VBLUR_SOURCE)
        self._vblur.channel_0 = self._hblur.texture

        self._combine = Shadertoy(size, _COMBINE_SOURCE)
        self._combine.channel_0 = self._scene.texture
        self._combine.channel_1 = self._vblur.texture

    @property
    def fbo(self):
        """The offscreen target to draw the bloom-affected scene into."""
        return self._scene.fbo

    def use(self):
        self._scene.fbo.use()

    def clear(self):
        self._scene.fbo.clear()

    def draw(self):
        """Run the bright-pass -> blur -> blur -> combine chain. Must be
        called with the desired final target (the window, by
        AlienInvasion's convention) already bound via target.use()."""
        self._bright_pass.render()
        self._hblur.render()
        self._vblur.render()
        self._combine.render()
