import os
import re
import subprocess
import sys

def export_mermaid_from_markdown(md_file_path, output_dir):
    if not os.path.exists(md_file_path):
        print(f"Error: {md_file_path} not found")
        return

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with open(md_file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find all mermaid blocks (accounting for possible indentation)
    mermaid_blocks = re.findall(r'^\s*```mermaid\n(.*?)\n\s*```', content, re.DOTALL | re.MULTILINE)

    if not mermaid_blocks:
        print("No mermaid blocks found.")
        return

    print(f"Found {len(mermaid_blocks)} mermaid blocks.")

    for i, block in enumerate(mermaid_blocks):
        # Generate a filename base (you could try to extract context from the heading above, but index is safer)
        # Try to find the preceding heading to give it a better name
        prefix = content[:content.find(block)].split('\n')
        suggested_name = f"diagram_{i+1}"
        for line in reversed(prefix):
            if line.startswith('###') or line.startswith('##'):
                clean_name = re.sub(r'[^a-zA-Z0-9\s]', '', line.lstrip('#').strip()).replace(' ', '_').lower()
                if clean_name:
                    suggested_name = f"{i+1}_{clean_name}"
                break

        mmd_file = os.path.join(output_dir, f"{suggested_name}.mmd")
        png_file = os.path.join(output_dir, f"{suggested_name}.png")

        # Write the mermaid code to a temp file
        with open(mmd_file, 'w', encoding='utf-8') as f:
            f.write(block)

        print(f"Converting diagram {i+1} to {png_file}...")
        
        # Use local mmdc (mermaid-cli) with higher resolution (scale = 3)
        mmdc_bin = os.path.join(repo_root, "node_modules", ".bin", "mmdc")
        try:
            result = subprocess.run([
                mmdc_bin,
                "-i", mmd_file,
                "-o", png_file,
                "-b", "white",
                "-s", "5"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"Successfully exported: {png_file}")
                # Clean up .mmd file
                os.remove(mmd_file)
            else:
                print(f"Failed to export: {png_file}")
                print(f"Error: {result.stderr}")
        except Exception as e:
            print(f"An error occurred: {e}")

if __name__ == "__main__":
    repo_root = "/Users/bronsonhill/Documents/Documents - Bronson’s MacBook Pro/Personal/Repositories/anthropic-multi-agent-system"
    md_file = os.path.join(repo_root, "docs/series-outline/1. How Anthropic Built a Multi-Agent Research System (Conceptual Overview).md")
    output_images = os.path.join(repo_root, "docs/series-outline/images/diagrams")
    
    export_mermaid_from_markdown(md_file, output_images)
