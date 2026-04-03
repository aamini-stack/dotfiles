return { -- Highlight, edit, and navigate code
  'nvim-treesitter/nvim-treesitter',
  build = ':TSUpdate',
  config = function()
    local filetypes = { 'bash', 'c', 'css', 'diff', 'html', 'javascript', 'json', 'lua', 'luadoc', 'markdown', 'markdown_inline', 'python', 'query', 'tsx', 'typescript', 'vim', 'vimdoc' }
    require('nvim-treesitter').setup()
    vim.api.nvim_create_autocmd('FileType', {
      pattern = filetypes,
      callback = function() vim.treesitter.start() end,
    })
  end,
}
