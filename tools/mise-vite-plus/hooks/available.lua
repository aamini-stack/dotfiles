local function split(value, separator)
	local parts = {}
	for part in value:gmatch("([^" .. separator .. "]+)") do
		parts[#parts + 1] = part
	end
	return parts
end

local function compare_pre(a, b)
	if not a and not b then
		return 0
	end
	if not a then
		return 1
	end
	if not b then
		return -1
	end

	local a_ids = split(a, ".")
	local b_ids = split(b, ".")
	for i = 1, math.max(#a_ids, #b_ids) do
		if not a_ids[i] then
			return -1
		end
		if not b_ids[i] then
			return 1
		end
		local an = tonumber(a_ids[i])
		local bn = tonumber(b_ids[i])
		if an and bn then
			if an ~= bn then
				return an < bn and -1 or 1
			end
		elseif an then
			return -1
		elseif bn then
			return 1
		elseif a_ids[i] ~= b_ids[i] then
			return a_ids[i] < b_ids[i] and -1 or 1
		end
	end
	return 0
end

local function version_less(a, b)
	local a_maj, a_min, a_pat, a_pre = a:match("^(%d+)%.(%d+)%.(%d+)%-?(.*)$")
	local b_maj, b_min, b_pat, b_pre = b:match("^(%d+)%.(%d+)%.(%d+)%-?(.*)$")
	if not a_maj and not b_maj then
		return a < b
	end
	if not a_maj then
		return true
	end
	if not b_maj then
		return false
	end
	a_maj, a_min, a_pat = tonumber(a_maj), tonumber(a_min), tonumber(a_pat)
	b_maj, b_min, b_pat = tonumber(b_maj), tonumber(b_min), tonumber(b_pat)
	if a_maj ~= b_maj then
		return a_maj < b_maj
	end
	if a_min ~= b_min then
		return a_min < b_min
	end
	if a_pat ~= b_pat then
		return a_pat < b_pat
	end
	return compare_pre(
		a_pre ~= "" and a_pre or nil,
		b_pre ~= "" and b_pre or nil
	) < 0
end

function PLUGIN:Available(ctx)
	local http = require("http")
	local json = require("json")
	local registry = require("registry")
	local response, err = http.get({ url = registry.package_url("vite-plus") })
	if err ~= nil then
		error("Failed to fetch Vite+ versions: " .. err)
	end
	if response.status_code ~= 200 then
		error("npm registry returned status " .. response.status_code)
	end

	local package = json.decode(response.body)
	local result = {}
	for version, _ in pairs(package.versions or {}) do
		local pre = version:match("^%d+%.%d+%.%d+%-(.+)$")
		if
			not pre
			or pre:match("^alpha%.")
			or pre:match("^beta%.")
			or pre:match("^rc%.")
		then
			table.insert(result, { version = version })
		end
	end
	table.sort(result, function(a, b)
		return version_less(b.version, a.version)
	end)
	return result
end
