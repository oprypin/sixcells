// Minimal Win32 application that runs a process relative to the folder it's in.

#include <windows.h>

int WINAPI WinMain(HINSTANCE hInstance, HINSTANCE hPrevInstance, LPSTR lpCmdLine, int nCmdShow)
{
    STARTUPINFO si;
    PROCESS_INFORMATION pi;
    char path[2048];
    long path_size;

    // Get absolute path to this executable
    path_size = GetModuleFileName(NULL, path, sizeof path);

    // Drop the executable name itself
    while (path[--path_size] != '\\');

    // Append a different path
    lstrcpy(path + path_size + 1, CMD);

    // Create default STARTUPINFO
    ZeroMemory(&si, sizeof(si));
    si.cb = sizeof(si);

    // Create default PROCESS_INFORMATION
    ZeroMemory(&pi, sizeof(pi));

    // Run the process
    CreateProcess(
        NULL, path,
        NULL, NULL, FALSE,
        0, NULL, NULL,
        &si, &pi
    );
}
