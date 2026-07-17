function setup(config)
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
end
