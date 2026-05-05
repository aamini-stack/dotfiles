return { -- Highlight, edit, and navigate code
  'nvim-treesitter/nvim-treesitter',
  build = ':TSUpdate',
  config = function()
    local parsers = { 'bash', 'c', 'css', 'diff', 'html', 'javascript', 'json', 'lua', 'luadoc', 'markdown', 'markdown_inline', 'python', 'query', 'tsx', 'typescript', 'vim', 'vimdoc' }
    require('nvim-treesitter').setup {}
    require('nvim-treesitter').install(parsers):wait(300000)
    vim.api.nvim_create_autocmd('FileType', {
      pattern = parsers,
      callback = function(args) vim.treesitter.start(args.buf) end,
    })
  end,
}
