function PLUGIN:PreInstall(ctx)
	local http = require("http")
	local json = require("json")
	local platform = require("platform")
	local registry = require("registry")
	local package = platform.package_name()
	local response, err = http.get({ url = registry.package_url(package) })
	if err ~= nil then
		error("Failed to resolve " .. package .. ": " .. err)
	end
	if response.status_code ~= 200 then
		error("npm registry returned status " .. response.status_code)
	end

	local metadata = json.decode(response.body)
	local release = metadata.versions and metadata.versions[ctx.version]
	if not release or not release.dist or not release.dist.tarball then
		error(
			"npm metadata has no tarball URL for "
				.. package
				.. "@"
				.. ctx.version
		)
	end
	return { version = ctx.version, url = release.dist.tarball }
end
