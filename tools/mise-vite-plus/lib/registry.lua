local M = {}

local function trim(value)
	return value:match("^%s*(.-)%s*$")
end

local function user_npmrc()
	local configured = os.getenv("NPM_CONFIG_USERCONFIG")
	if configured and configured ~= "" then
		return configured
	end

	local home = os.getenv("HOME") or os.getenv("USERPROFILE")
	if not home then
		return nil
	end
	return home .. "/.npmrc"
end

function M.url()
	local configured = os.getenv("NPM_CONFIG_REGISTRY")
	if configured and configured ~= "" then
		return configured:gsub("/+$", "")
	end

	local path = user_npmrc()
	local npmrc = path and io.open(path, "r") or nil
	if npmrc then
		for line in npmrc:lines() do
			local value = line:match("^%s*registry%s*=%s*(.-)%s*$")
			if value then
				npmrc:close()
				return trim(value):gsub("/+$", "")
			end
		end
		npmrc:close()
	end

	return "https://registry.npmjs.org"
end

function M.package_url(package)
	return M.url() .. "/" .. package:gsub("/", "%%2f")
end

return M
