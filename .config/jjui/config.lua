local WORKSPACE_LIST_TEMPLATE = [[self.name() ++ "\t" ++ self.root() ++ "\n"]]

local function current_workspace_root()
  local out = jj("root")
  if not out then return nil end
  return (out:gsub("%s+$", ""))
end

local function list_workspaces()
  local out, err = jj("workspace", "list", "-T", WORKSPACE_LIST_TEMPLATE)
  if not out then return nil, err end
  local workspaces = {}
  for line in out:gmatch("[^\n]+") do
    local name, root = line:match("^(.-)\t(.+)$")
    if name and root then
      table.insert(workspaces, { name = name, root = root })
    end
  end
  return workspaces
end

local function current_workspace_name()
  local root = current_workspace_root()
  local workspaces = list_workspaces()
  if not root or not workspaces then return nil end
  for _, ws in ipairs(workspaces) do
    if ws.root == root then return ws.name end
  end
end

function setup(config)
  config.action("switch workspace", function()
    local workspaces, err = list_workspaces()
    if not workspaces then
      flash({ text = "workspace list failed: " .. tostring(err), error = true })
      return
    end

    local current = current_workspace_root()
    local options = {}
    for _, ws in ipairs(workspaces) do
      local marker = ws.root == current and "* " or "  "
      table.insert(options, marker .. ws.name .. "  (" .. ws.root .. ")")
    end

    local choice = choose({ options = options, title = "Switch workspace" })
    if not choice then return end

    for i, option in ipairs(options) do
      if option == choice then
        local ws = workspaces[i]
        local ok, werr = change_workspace(ws.root)
        if not ok then
          flash({ text = "switch failed: " .. tostring(werr), error = true })
          return
        end
        revisions.refresh()
        flash({ text = "workspace: " .. ws.name, sticky = true })
        return
      end
    end
  end, {
    desc = "switch workspace",
    seq = { "w", "w" },
    scope = "revisions",
  })

  config.action("create workspace here", function()
    local change_id = context.change_id()
    if not change_id or change_id == "" then
      flash({ text = "No revision selected", error = true })
      return
    end

    local name = input({ title = "Create workspace", prompt = "name: " })
    if not name then return end
    name = name:gsub("^%s+", ""):gsub("%s+$", "")
    if name == "" then return end

    exec_shell(string.format("wt new %q -r %q", name, change_id))
  end, {
    desc = "create workspace here",
    seq = { "w", "c" },
    scope = "revisions",
  })

  config.action("show current workspace", function()
    local name = current_workspace_name()
    if name then
      flash({ text = "workspace: " .. name, sticky = true })
    else
      flash({ text = "Could not determine current workspace", error = true })
    end
  end, {
    desc = "show current workspace",
    seq = { "w", "i" },
    scope = "revisions",
  })

  config.action("open revision in Hunk", function()
    local change_id = context.change_id()
    if not change_id or change_id == "" then
      flash({ text = "No revision selected", error = true })
      return
    end

    exec_shell(string.format("hunk show %q", change_id))
  end, {
    desc = "open revision in Hunk",
    key = "d",
    scope = "revisions",
  })

  config.action("open file diff in Hunk", function()
    local change_id = context.change_id()
    local file = context.file()
    if not change_id or change_id == "" or not file or file == "" then
      flash({ text = "No file selected", error = true })
      return
    end

    exec_shell(string.format("hunk show %q -- %q", change_id, file))
  end, {
    desc = "open file diff in Hunk",
    key = "enter",
    scope = "revisions.details",
  })

  config.action("open file in nvim", function()
    local file = context.file()
    if not file or file == "" then
      flash({ text = "No file selected", error = true })
      return
    end

    exec_shell(string.format("nvim %q", file))
  end, {
    desc = "open file in nvim",
    key = "e",
    scope = "revisions.details",
  })
end
