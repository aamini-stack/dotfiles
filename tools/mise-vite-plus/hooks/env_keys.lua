function PLUGIN:EnvKeys(ctx)
	local file = require("file")
	return { { key = "PATH", value = file.join_path(ctx.path, "bin") } }
end
