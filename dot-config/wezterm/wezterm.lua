local wezterm = require("wezterm")
local act = wezterm.action

-- Table to store status_text per window ID
local window_status_texts = {}

wezterm.on("update-status", function(window, pane)
	local dimensions = pane:get_dimensions()
	local cols = dimensions and dimensions.cols or "N/A"
	local rows = dimensions and dimensions.viewport_rows or "N/A"

	-- Create a status text with window size
	local status_text = string.format("  %sx%s", cols, rows)

	-- Store status_text in the table with window ID as the key
	window_status_texts[pane:pane_id()] = status_text
end)

wezterm.on("format-window-title", function(tab, pane, tabs, panes, config)
	local zoomed = ""
	local id = tab.active_pane.pane_id
	if tab.active_pane.is_zoomed then
		zoomed = "[Z] "
	end
	local index = ""
	if #tabs > 1 then
		index = string.format("[%d/%d] ", tab.tab_index + 1, #tabs)
	end
	-- Retrieve the status_text for the current window using window ID
	local status_text = window_status_texts[id] or ""
	return zoomed .. index .. tab.active_pane.title .. status_text
end)

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

config.enable_tab_bar = false

config.use_resize_increments = true

return config
