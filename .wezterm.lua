local wezterm = require 'wezterm'
local act = wezterm.action

local config = {}
if wezterm.config_builder then
  config = wezterm.config_builder()
end

config.keys = {
  -- paste from the clipboard
  { key = 'v', mods = 'CTRL', action = act.PasteFrom 'Clipboard' },
  { key = 'V', mods = 'CTRL', action = act.PasteFrom 'Clipboard' },

  -- paste from the primary selection
  { key = 'v', mods = 'CTRL', action = act.PasteFrom 'PrimarySelection' },
  { key = 'V', mods = 'CTRL', action = act.PasteFrom 'PrimarySelection' },
}

config.color_scheme = "Catppuccin Mocha"
config.font = wezterm.font('JetBrains Mono')

config.default_domain = 'WSL:Ubuntu'
return config
