import os
import subprocess
import glob
import shutil

def run_command(command):
    try:
        subprocess.run(command, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {command}\n{e}")

def sanitize():
    print(":::group:::Sanitizing Codebase")

    # 0. Revert upstream oos* -> a* directory renames.
    #    The fork's build-kernel-release.yml hardcodes OOS naming
    #    (e.g. (.os_version | gsub("OOS"; "") | tonumber)), which crashes
    #    on "A15".  Upstream renamed configs/{oos14,oos15,oos16} ->
    #    {a14,a15,a16} and manifests likewise.  Git rename-detection
    #    normally keeps files at the oos* paths during merge, but this
    #    is a safety net for any edge case where a* dirs appear.
    for ver in ["14", "15", "16"]:
        for base in ["configs", "manifests"]:
            a_dir = os.path.join(base, f"a{ver}")
            oos_dir = os.path.join(base, f"oos{ver}")
            if os.path.isdir(a_dir):
                if os.path.isdir(oos_dir):
                    # Both exist: copy new files from a_dir into oos_dir,
                    # then remove a_dir.
                    run_command(f"cp -rn {a_dir}/* {oos_dir}/ 2>/dev/null || true")
                    shutil.rmtree(a_dir)
                else:
                    os.rename(a_dir, oos_dir)
                print(f"Renamed {a_dir} -> {oos_dir}")

    # 1. Update manifest XMLs
    xml_files = glob.glob("manifests/**/*.xml", recursive=True)
    for xml_file in xml_files:
        run_command(f"sed -i 's|github.com/WildKernels/AnyKernel3|github.com/huangdihd/AnyKernel3|g' {xml_file}")
        run_command(f"sed -i 's|fetch=\"https://github.com/WildKernels\" name=\"wild\"|fetch=\"https://github.com/huangdihd\" name=\"wild\"|g' {xml_file}")
        run_command(f"sed -i -E 's/(name=\"AnyKernel3\".*revision=\")[^\"]+(\")/\\1gki-2.0\\2/g' {xml_file}")

    # 2. Update config JSONs: uname + os_version
    json_files = glob.glob("configs/**/*.json", recursive=True)
    for json_file in json_files:
        run_command(f"sed -i 's/\"uname\": \"OP-WILD\"/\"uname\": \"OP-BAKASU\"/g' {json_file}")
        # Revert upstream's OOS1x -> A1x rename in os_version; the fork's
        # build-kernel-release.yml needs "OOS14"/"OOS15"/"OOS16".
        run_command(f"sed -i 's/\"os_version\": \"A14\"/\"os_version\": \"OOS14\"/g' {json_file}")
        run_command(f"sed -i 's/\"os_version\": \"A15\"/\"os_version\": \"OOS15\"/g' {json_file}")
        run_command(f"sed -i 's/\"os_version\": \"A16\"/\"os_version\": \"OOS16\"/g' {json_file}")

    # 3. Update build-kernel action.yml AnyKernel3 URL
    action_path = ".github/actions/build-kernel/action.yml"
    if os.path.exists(action_path):
        run_command(f"sed -i 's|https://github.com/WildKernels/AnyKernel3|https://github.com/huangdihd/AnyKernel3|g' {action_path}")

        # 4. Remove KernelSU-Next / KSUN steps
        with open(action_path, 'r') as f:
            lines = f.readlines()

        new_lines = []
        skip = False
        for line in lines:
            if '- name: Add KernelSU-Next' in line or '- name: Add KSUN' in line:
                skip = True
            elif skip and line.startswith('    - name:'):
                skip = False

            if not skip:
                new_lines.append(line)

        with open(action_path, 'w') as f:
            f.writelines(new_lines)

    # 5. Delete Kernel Monitor Workflow
    monitor_workflow = ".github/workflows/oplus-kernel-monitor.yml"
    if os.path.exists(monitor_workflow):
        os.remove(monitor_workflow)
        print(f"Deleted {monitor_workflow}")

    print(":::endgroup:::")

if __name__ == "__main__":
    sanitize()
