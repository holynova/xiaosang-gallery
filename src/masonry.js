let arrangedColumns;
function arrangeGrid(grid) {
  const style = getComputedStyle(grid);
  const cols = Number(style.getPropertyValue('--columns'));
  const gap = Number.parseFloat(style.getPropertyValue('--gap'));
  const items = [...grid.querySelectorAll('.art-card')];
  if (arrangedColumns !== cols) {
    items.forEach(item => item.style.gridColumnStart = '');
    arrangedColumns = cols;
  }
  const heights = items.map(item => item.offsetHeight);
  const lengths = Array(cols).fill(1);
  items.forEach((item,i) => {
    const column = lengths.indexOf(Math.min(...lengths));
    item.style.gridColumnStart = column+1;
    item.style.gridRow = lengths[column] + ' / span ' + Math.max(1,heights[i]);
    lengths[column] += heights[i]+gap;
  });
}
arrangeGrid(document.getElementById('masonry'));
