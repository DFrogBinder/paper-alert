# LazyVim Glow Markdown Preview Setup

Use `glow.nvim` to render Markdown buffers automatically inside LazyVim.

## 1. Install the `glow` CLI

Glow is an external binary `glow.nvim` shells out to. Install it using your platform’s package manager and verify it works.

```sh
# macOS (Homebrew)
brew install glow

# Debian / Ubuntu
sudo apt install glow

# Arch Linux
sudo pacman -S glow

# Windows (scoop)
scoop install glow

glow --version
```

## 2. Enable the Markdown extra

LazyVim ships an extra that wires up `ellisonleao/glow.nvim`. Add it to `~/.config/nvim/lua/config/lazy.lua` so it’s imported during plugin bootstrap.

```sh
nvim ~/.config/nvim/lua/config/lazy.lua
```

Inside the `require("lazy").setup({ ... })` call, add:

```lua
{ import = "lazyvim.plugins.extras.lang.markdown" },
```

Save and quit with `:wq`.

## 3. Auto-launch Glow for Markdown files

Create a plugin spec that triggers Glow whenever a `*.md` buffer is read.

```sh
nvim ~/.config/nvim/lua/plugins/glow_auto.lua
```

Paste the following (adjust if you already have a plugins directory structure):

```lua
return {
  "ellisonleao/glow.nvim",
  ft = "markdown",
  config = function(_, opts)
    require("glow").setup(opts)

    vim.api.nvim_create_autocmd("BufReadPost", {
      pattern = "*.md",
      callback = function()
        -- Close any stale preview before opening a fresh one
        pcall(vim.cmd, "GlowStop")
        vim.cmd("Glow")
      end,
    })
  end,
}
```

Save with `:wq`.

## 4. Sync plugins

Pull in the new dependency and compile LazyVim:

```sh
nvim --headless "+Lazy! sync" +qa
```

The next regular Neovim launch will have Glow available.

## 5. Try it out

Open a Markdown file and the preview should appear automatically:

```sh
nvim docs/readme.md
```

- Close the preview window with `q` while it is focused, or run `:GlowStop`.
- Manually reopen it with `:Glow` if you close it and want to see the preview again.

That’s it—LazyVim now renders Markdown files with Glow as soon as you open them.
