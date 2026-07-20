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

local function find_workspace(workspaces, root, name)
  for _, ws in ipairs(workspaces) do
    if ws.root == root then return ws end
  end
  for _, ws in ipairs(workspaces) do
    if ws.name == name then return ws end
  end
end

local function record_workspace(root)
  local result_path = os.getenv("JJUI_WORKSPACE_RESULT_FILE")
  if not result_path or result_path == "" then return true end

  local file, err = io.open(result_path, "w")
  if not file then return nil, err end
  local ok, write_err = file:write(root)
  local closed, close_err = file:close()
  if not ok then return nil, write_err end
  if not closed then return nil, close_err end
  return true
end

local function switch_workspace(ws)
  local ok, err = change_workspace(ws.root)
  if not ok then
    flash({ text = "switch failed: " .. tostring(err), error = true })
    return
  end

  local recorded, record_err = record_workspace(ws.root)
  if not recorded then
    flash({ text = "shell handoff failed: " .. tostring(record_err), error = true })
  end
  revisions.refresh()
  flash("workspace: " .. ws.name)
end

function setup(config)
  config.action("switch workspace", function()
    local workspaces, err = list_workspaces()
    if not workspaces then
      flash({ text = "workspace list failed: " .. tostring(err), error = true })
      return
    end

    local current = current_workspace_root()
    local ordered = {}
    for _, ws in ipairs(workspaces) do
      if ws.root == current then table.insert(ordered, ws) end
    end
    for _, ws in ipairs(workspaces) do
      if ws.root ~= current then table.insert(ordered, ws) end
    end

    local options = {}
    for _, ws in ipairs(ordered) do
      local marker = ws.root == current and "* [current] " or "  "
      table.insert(options, marker .. ws.name .. "  (" .. ws.root .. ")")
    end

    local choice = choose({ options = options, title = "Switch workspace", ordered = true })
    if not choice then return end

    for i, option in ipairs(options) do
      if option == choice then
        switch_workspace(ordered[i])
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

    local result_path = os.tmpname()
    exec_shell(string.format("WT_RESULT_FILE=%q command wt new %q -r %q", result_path, name, change_id))

    local result = io.open(result_path, "r")
    if not result then return end
    local root = result:read("*a"):gsub("%s+$", "")
    result:close()
    os.remove(result_path)
    if root == "" then return end

    local updated, err = list_workspaces()
    if not updated then
      flash({ text = "workspace list failed: " .. tostring(err), error = true })
      return
    end
    local ws = find_workspace(updated, root, name)
    if not ws then
      flash({ text = "created workspace not found: " .. name, error = true })
      return
    end
    switch_workspace(ws)
  end, {
    desc = "create workspace here",
    seq = { "w", "c" },
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
