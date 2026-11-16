let arrangedWidth, columnLengths=[], arrangedCount=0;
function arrangeGrid(grid, appendedFrom=0) {
  if (!grid.firstElementChild?.classList.contains('art-card')) {
    arrangedCount = 0;
    return;
  }
  const style = getComputedStyle(grid);
  const cols = Number(style.getPropertyValue('--columns'));
  const gap = Number.parseFloat(style.getPropertyValue('--gap'));
  const width = grid.clientWidth;
  const reuse = appendedFrom > 0 && appendedFrom === arrangedCount && width === arrangedWidth && cols === columnLengths.length;
  const items = [...grid.children].slice(reuse ? appendedFrom : 0);
  if (!reuse) {
    items.forEach(item => item.style.gridColumnStart = '');
    columnLengths = Array(cols).fill(1);
  }
  const heights = items.map(item => item.offsetHeight);
  items.forEach((item,i) => {
    const column = columnLengths.indexOf(Math.min(...columnLengths));
    item.style.gridColumnStart = column+1;
    item.style.gridRow = columnLengths[column] + ' / span ' + Math.max(1,heights[i]);
    columnLengths[column] += heights[i]+gap;
  });
  arrangedWidth = width;
  arrangedCount = grid.children.length;
}
function revealThumbnail(img) {
  const source = img.previousElementSibling;
  source.srcset = source.dataset.srcset;
  img.srcset = img.dataset.srcset;
  img.src = img.dataset.src;
  delete img.dataset.src;
}

const thumbnailObserver = 'IntersectionObserver' in window ? new IntersectionObserver(entries => {
  for (const entry of entries) {
    if (!entry.isIntersecting) continue;
    thumbnailObserver.unobserve(entry.target);
    if (entry.target.isConnected) revealThumbnail(entry.target);
  }
}) : null;

function observeThumbnails(grid) {
  for (const img of grid.querySelectorAll('img[data-src]')) {
    if (thumbnailObserver) thumbnailObserver.observe(img);
    else revealThumbnail(img);
  }
}

const initialGrid = document.getElementById('masonry');
arrangeGrid(initialGrid);
if (!new URLSearchParams(location.search).get('series')) observeThumbnails(initialGrid);
