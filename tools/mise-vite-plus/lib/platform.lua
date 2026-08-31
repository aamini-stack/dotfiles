local M = {}

local function os_token()
	if RUNTIME.osType == "darwin" then
		return "darwin"
	end
	if RUNTIME.osType == "linux" then
		return "linux"
	end
	if RUNTIME.osType == "windows" then
		return "win32"
	end
	error("Unsupported operating system: " .. tostring(RUNTIME.osType))
end

local function arch_token()
	if RUNTIME.archType == "arm64" then
		return "arm64"
	end
	if RUNTIME.archType == "amd64" then
		return "x64"
	end
	error("Unsupported architecture: " .. tostring(RUNTIME.archType))
end

function M.suffix()
	local os = os_token()
	local arch = arch_token()
	if os == "linux" then
		return os .. "-" .. arch .. "-gnu"
	end
	if os == "win32" then
		return os .. "-" .. arch .. "-msvc"
	end
	return os .. "-" .. arch
end

function M.package_name()
	return "@voidzero-dev/vite-plus-cli-" .. M.suffix()
end

function M.binary_name()
	return RUNTIME.osType == "windows" and "vp.exe" or "vp"
end

return M
