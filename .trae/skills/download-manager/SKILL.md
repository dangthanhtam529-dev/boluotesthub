# Download Manager

This skill controls all download operations to ensure files are saved to the current working directory and prevents any downloads to the C: drive (system drive).

## When to Invoke

**Invoke IMMEDIATELY when:**
- User asks to download any file
- User asks to fetch content from a URL
- User asks to save, export, or saveas any file
- User asks to create a skill that involves downloading
- Any download operation is required

**This skill MUST be called FIRST before any download-related tool usage.**

## Rules

### 1. Current Working Directory
- All downloads MUST go to: `g:\agent_eaplore\full-stack-fastapi-template-master` (current working directory)
- Never download to C:\ or any other drive
- Use absolute paths starting from current directory

### 2. Allowed Download Destinations
- Current working directory: `g:\agent_eaplore\full-stack-fastapi-template-master`
- Any subdirectory within the current directory
- Examples:
  - ✅ `g:\agent_eaplore\full-stack-fastapi-template-master\downloads\file.zip`
  - ✅ `g:\agent_eaplore\full-stack-fastapi-template-master\assets\image.png`
  - ✅ `g:\agent_eaplore\full-stack-fastapi-template-master\`

### 3. Forbidden Destinations
- ❌ C:\ (any path starting with C:)
- ❌ Any other system drive
- ❌ Paths containing `C:` in any form
- ❌ Absolute paths pointing outside current directory

### 4. Tools Usage Guidelines

#### WebFetch / WebSearch
- Fetch web content and save to current directory
- Use descriptive filenames based on content
- Save path: `g:\agent_eaplore\full-stack-fastapi-template-master\`

#### Write Tool
- If saving downloaded content, use paths relative to current directory
- Example: `downloads\filename.ext` → saves to `g:\agent_eaplore\full-stack-fastapi-template-master\downloads\filename.ext`

#### Bash/Download Commands
- Always specify output path in current directory
- Use `-O` or `--output` flags with paths starting from `g:\agent_eaplore\full-stack-fastapi-template-master`

### 5. Validation Steps

Before any download:
1. Check if target path contains `C:` or other system drives
2. If yes, REJECT and inform user
3. Always use paths within `g:\agent_eaplore\full-stack-fastapi-template-master`

## Examples

### ✅ Correct Usage
```
User: Download this PDF to the project folder
Action: Save to g:\agent_eaplore\full-stack-fastapi-template-master\document.pdf

User: Fetch the webpage and save it
Action: Use WebFetch to get content, save to g:\agent_eaplore\full-stack-fastapi-template-master\index.html
```

### ❌ Incorrect Usage
```
User: Download to C:\Users\Documents
Action: REJECT - Cannot download to C: drive

User: Save to desktop
Action: REJECT - Desktop is typically on C: drive
```

## Error Handling

If user requests download to C: drive or outside current directory:
1. Politely refuse
2. Explain: "I cannot download to C: drive due to limited system disk space. All downloads must go to the current working directory: `g:\agent_eaplore\full-stack-fastapi-template-master`"
3. Offer to save to current directory instead
4. Wait for user confirmation before proceeding

## Special Cases

### Skill Creation with Downloads
If creating a skill that requires downloading templates or assets:
1. Use current working directory for all file operations
2. Store skill in: `.trae/skills/<skill-name>/`
3. Download any assets to current directory first

### Project-Specific Downloads
If downloading project-related files:
1. Always use `g:\agent_eaplore\full-stack-fastapi-template-master` as base
2. Create subdirectories as needed (e.g., `downloads/`, `assets/`)

## Implementation Checklist

For every download operation:
- [ ] Verify target path does not start with C:
- [ ] Use absolute path `g:\agent_eaplore\full-stack-fastapi-template-master` as base
- [ ] Inform user where file will be saved
- [ ] Confirm save location if uncertain
