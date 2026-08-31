function PLUGIN:PostInstall(ctx)
	local file = require("file")
	local platform = require("platform")
	local registry = require("registry")
	local sdk = ctx.sdkInfo[PLUGIN.name]
	local path = sdk.path
	local version = sdk.version
	local binary = platform.binary_name()
	local is_windows = RUNTIME.osType == "windows"
	local package_binary = file.join_path(path, "package", binary)
	local direct_binary = file.join_path(path, binary)
	local source = file.exists(package_binary) and package_binary
		or direct_binary
	if not file.exists(source) then
		error("Could not find " .. binary .. " in " .. path)
	end

	local bin = file.join_path(path, "bin")
	os.execute('mkdir -p "' .. bin .. '"')
	local destination = file.join_path(bin, binary)
	if os.execute('mv "' .. source .. '" "' .. destination .. '"') ~= 0 then
		error("Failed to install " .. binary)
	end
	if not is_windows then
		os.execute('chmod +x "' .. destination .. '"')
	end

	if is_windows then
		os.execute(
			'copy "'
				.. destination
				.. '" "'
				.. file.join_path(bin, "vpx.exe")
				.. '"'
		)
		os.execute(
			'copy "'
				.. destination
				.. '" "'
				.. file.join_path(bin, "vpr.exe")
				.. '"'
		)
	else
		os.execute('ln -sf vp "' .. file.join_path(bin, "vpx") .. '"')
		os.execute('ln -sf vp "' .. file.join_path(bin, "vpr") .. '"')
	end

	local package_json =
		assert(io.open(file.join_path(path, "package.json"), "w"))
	package_json:write(
		'{\n  "name": "vp-global",\n  "version": "'
			.. version
			.. '",\n  "private": true,\n  "dependencies": {\n    "vite-plus": "'
			.. version
			.. '"\n  }\n}\n'
	)
	package_json:close()

	local npmrc = assert(io.open(file.join_path(path, ".npmrc"), "w"))
	npmrc:write(
		"registry="
			.. registry.url()
			.. "\nminimum-release-age=0\nmin-release-age=0\n"
	)
	npmrc:close()

	local install_log = file.join_path(path, "install.log")
	local npm = is_windows and "npm.cmd" or "npm"
	local command = 'cd "'
		.. path
		.. '" && CI=true '
		.. npm
		.. ' install --ignore-scripts --legacy-peer-deps > "'
		.. install_log
		.. '" 2>&1'
	if is_windows then
		command = 'cd /d "'
			.. path
			.. '" && set CI=true && '
			.. npm
			.. ' install --ignore-scripts --legacy-peer-deps > "'
			.. install_log
			.. '" 2>&1'
	end
	if os.execute(command) ~= 0 then
		local log = io.open(install_log, "r")
		local output = log and log:read("*a") or ""
		if log then
			log:close()
		end
		error("Failed to install Vite+ JS dependencies. Log:\n" .. output)
	end

	local home = os.getenv("HOME") or os.getenv("USERPROFILE")
	local vite_plus_home = file.join_path(home, ".vite-plus")
	os.execute('mkdir -p "' .. vite_plus_home .. '"')
	local current = file.join_path(vite_plus_home, "current")
	if is_windows then
		os.execute('cmd /c rmdir "' .. current .. '" 2>nul')
		os.execute('cmd /c mklink /J "' .. current .. '" "' .. path .. '"')
	else
		os.execute('ln -sfn "' .. path .. '" "' .. current .. '"')
	end

	local env_output = is_windows and "nul" or "/dev/null"
	if
		os.execute(
			'"'
				.. destination
				.. '" env setup --env-only > '
				.. env_output
				.. " 2>&1"
		) ~= 0
	then
		io.stderr:write("warn: vp env setup --env-only failed\n")
	end
	local package_dir = file.join_path(path, "package")
	if file.exists(package_dir) then
		os.execute('rm -rf "' .. package_dir .. '"')
	end
end
