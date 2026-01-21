local wezterm = require("wezterm")
local act = wezterm.action

local config = {}
if wezterm.config_builder then
	config = wezterm.config_builder()
end

config.keys = {
	-- paste from the clipboard
	{ key = "v", mods = "CTRL", action = act.PasteFrom("Clipboard") },
	{ key = "V", mods = "CTRL", action = act.PasteFrom("Clipboard") },

	-- paste from the primary selection
	{ key = "v", mods = "CTRL", action = act.PasteFrom("PrimarySelection") },
	{ key = "V", mods = "CTRL", action = act.PasteFrom("PrimarySelection") },
}

config.color_scheme = "Catppuccin Mocha"
config.font = wezterm.font("JetBrains Mono")

config.window_background_opacity = 0.75
config.macos_window_background_blur = 20

-- Enable tab bar to show clock in right status
config.enable_tab_bar = true
config.use_fancy_tab_bar = false
config.show_tabs_in_tab_bar = true
config.hide_tab_bar_if_only_one_tab = false
wezterm.on("update-right-status", function(window)
	local date = wezterm.strftime("%H:%M  %b %d")
	window:set_right_status(wezterm.format({
		{ Foreground = { Color = "#7aa2f7" } },
		{ Text = date },
	}))
end)

return config
