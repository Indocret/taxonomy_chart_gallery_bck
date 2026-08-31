const manifestPath = './charts/manifest.json';
const chartGrid = document.getElementById('chartGrid');
const statusNode = document.getElementById('status');
const tileSize = 256;
const maxSatelliteZoom = 19;

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function renderEmpty(message, className = 'empty-state') {
  chartGrid.innerHTML = `<div class="${className}">${escapeHtml(message)}</div>`;
}

function validCoordinate(coordinate) {
  return Array.isArray(coordinate)
    && Number.isFinite(coordinate[0])
    && Number.isFinite(coordinate[1]);
}

function collectBoundaryRings(geojson, rings = []) {
  if (!geojson) {
    return rings;
  }

  if (geojson.type === 'FeatureCollection') {
    (geojson.features || []).forEach((feature) => collectBoundaryRings(feature, rings));
    return rings;
  }

  if (geojson.type === 'Feature') {
    collectBoundaryRings(geojson.geometry, rings);
    return rings;
  }

  if (geojson.type === 'GeometryCollection') {
    (geojson.geometries || []).forEach((geometry) => collectBoundaryRings(geometry, rings));
    return rings;
  }

  if (geojson.type === 'Polygon') {
    geojson.coordinates.forEach((ring) => {
      const coordinates = ring.filter(validCoordinate);

      if (coordinates.length > 1) {
        rings.push(coordinates);
      }
    });
  }

  if (geojson.type === 'MultiPolygon') {
    geojson.coordinates.forEach((polygon) => {
      polygon.forEach((ring) => {
        const coordinates = ring.filter(validCoordinate);

        if (coordinates.length > 1) {
          rings.push(coordinates);
        }
      });
    });
  }

  return rings;
}

function boundsFromRings(rings) {
  const bounds = {
    minLon: Infinity,
    maxLon: -Infinity,
    minLat: Infinity,
    maxLat: -Infinity,
  };

  rings.forEach((ring) => {
    ring.forEach(([lon, lat]) => {
      bounds.minLon = Math.min(bounds.minLon, lon);
      bounds.maxLon = Math.max(bounds.maxLon, lon);
      bounds.minLat = Math.min(bounds.minLat, lat);
      bounds.maxLat = Math.max(bounds.maxLat, lat);
    });
  });

  return Number.isFinite(bounds.minLon) ? bounds : null;
}

function clampLatitude(latitude) {
  return Math.max(-85.05112878, Math.min(85.05112878, latitude));
}

function lonLatToWorldPixel(lon, lat, zoom) {
  const scale = tileSize * 2 ** zoom;
  const clampedLat = clampLatitude(lat);
  const sinLat = Math.sin((clampedLat * Math.PI) / 180);

  return {
    x: ((lon + 180) / 360) * scale,
    y: (0.5 - Math.log((1 + sinLat) / (1 - sinLat)) / (4 * Math.PI)) * scale,
  };
}

function chooseZoom(bounds, width, height) {
  for (let zoom = maxSatelliteZoom; zoom >= 1; zoom -= 1) {
    const topLeft = lonLatToWorldPixel(bounds.minLon, bounds.maxLat, zoom);
    const bottomRight = lonLatToWorldPixel(bounds.maxLon, bounds.minLat, zoom);
    const projectedWidth = Math.abs(bottomRight.x - topLeft.x);
    const projectedHeight = Math.abs(bottomRight.y - topLeft.y);

    if (projectedWidth <= width * 0.72 && projectedHeight <= height * 0.72) {
      return zoom;
    }
  }

  return 1;
}

function tileUrl(x, y, zoom) {
  const tileCount = 2 ** zoom;
  const wrappedX = ((x % tileCount) + tileCount) % tileCount;

  return `https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/${zoom}/${y}/${wrappedX}`;
}

function loadImage(src) {
  return new Promise((resolve) => {
    const image = new Image();

    image.onload = () => resolve(image);
    image.onerror = () => resolve(null);
    image.src = src;
  });
}

function drawPreviewBase(context, width, height) {
  context.fillStyle = '#d7ded9';
  context.fillRect(0, 0, width, height);
}

async function drawSatelliteTiles(context, topLeft, zoom, width, height) {
  const tileCount = 2 ** zoom;
  const minTileX = Math.floor(topLeft.x / tileSize);
  const maxTileX = Math.floor((topLeft.x + width) / tileSize);
  const minTileY = Math.max(0, Math.floor(topLeft.y / tileSize));
  const maxTileY = Math.min(tileCount - 1, Math.floor((topLeft.y + height) / tileSize));
  const tilePromises = [];

  for (let tileX = minTileX; tileX <= maxTileX; tileX += 1) {
    for (let tileY = minTileY; tileY <= maxTileY; tileY += 1) {
      tilePromises.push(
        loadImage(tileUrl(tileX, tileY, zoom)).then((image) => ({
          image,
          tileX,
          tileY,
        }))
      );
    }
  }

  const tiles = await Promise.all(tilePromises);

  tiles.forEach(({ image, tileX, tileY }) => {
    if (!image) {
      return;
    }

    context.drawImage(
      image,
      tileX * tileSize - topLeft.x,
      tileY * tileSize - topLeft.y,
      tileSize,
      tileSize
    );
  });

  context.fillStyle = 'rgba(8, 34, 32, 0.08)';
  context.fillRect(0, 0, width, height);
}

function drawBoundaryRings(context, rings, topLeft, zoom) {
  const drawRings = () => {
    rings.forEach((ring) => {
      context.beginPath();

      ring.forEach(([lon, lat], index) => {
        const point = lonLatToWorldPixel(lon, lat, zoom);
        const x = point.x - topLeft.x;
        const y = point.y - topLeft.y;

        if (index === 0) {
          context.moveTo(x, y);
        } else {
          context.lineTo(x, y);
        }
      });

      context.closePath();
      context.stroke();
    });
  };

  context.save();
  context.lineJoin = 'round';
  context.lineCap = 'round';
  context.strokeStyle = 'rgba(0, 0, 0, 0.72)';
  context.lineWidth = 5;
  drawRings();
  context.strokeStyle = '#f8f7ef';
  context.lineWidth = 3;
  drawRings();
  context.strokeStyle = '#20c997';
  context.lineWidth = 2;
  drawRings();
  context.restore();
}

function setCanvasSize(canvas) {
  const bounds = canvas.getBoundingClientRect();
  const width = Math.max(240, Math.round(bounds.width || 320));
  const height = Math.max(135, Math.round(bounds.height || 180));
  const pixelRatio = Math.min(window.devicePixelRatio || 1, 2);

  canvas.width = Math.round(width * pixelRatio);
  canvas.height = Math.round(height * pixelRatio);

  const context = canvas.getContext('2d');
  context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);

  return { context, width, height };
}

async function renderMapPreview(canvas, geojsonHref) {
  const { context, width, height } = setCanvasSize(canvas);

  drawPreviewBase(context, width, height);

  try {
    const response = await fetch(geojsonHref, { cache: 'no-store' });

    if (!response.ok) {
      throw new Error(`Could not load ${geojsonHref}`);
    }

    const geojson = await response.json();
    const rings = collectBoundaryRings(geojson);
    const bounds = boundsFromRings(rings);

    if (!bounds) {
      throw new Error('No polygon boundary found.');
    }

    const zoom = chooseZoom(bounds, width, height);
    const centerLon = (bounds.minLon + bounds.maxLon) / 2;
    const centerLat = (bounds.minLat + bounds.maxLat) / 2;
    const center = lonLatToWorldPixel(centerLon, centerLat, zoom);
    const topLeft = {
      x: center.x - width / 2,
      y: center.y - height / 2,
    };

    await drawSatelliteTiles(context, topLeft, zoom, width, height);
    drawBoundaryRings(context, rings, topLeft, zoom);
  } catch (error) {
    context.fillStyle = '#5d7180';
    context.font = '13px Arial, Helvetica, sans-serif';
    context.fillText('Boundary preview unavailable', 14, height - 16);
  }
}

function renderMapFrame(sample) {
  if (!sample.geojson?.href) {
    return null;
  }

  const frame = document.createElement('figure');
  frame.className = 'map-preview';

  const canvas = document.createElement('canvas');
  canvas.setAttribute('aria-label', `Boundary preview for ${sample.title || sample.slug}`);

  const credit = document.createElement('span');
  credit.className = 'map-credit';
  credit.textContent = 'Imagery: Esri';

  frame.appendChild(canvas);
  frame.appendChild(credit);

  requestAnimationFrame(() => renderMapPreview(canvas, sample.geojson.href));

  return frame;
}

function renderSample(sample) {
  const article = document.createElement('article');
  article.className = 'chart-card';

  const heading = document.createElement('h3');
  heading.textContent = sample.title || sample.slug;

  const description = document.createElement('p');
  description.textContent = sample.description || 'Open the charts and entire taxonomy.';

  article.appendChild(heading);
  article.appendChild(description);

  const mapFrame = renderMapFrame(sample);

  if (mapFrame) {
    article.appendChild(mapFrame);
  }

  const links = document.createElement('div');
  links.className = 'chart-links';

  (sample.links || []).forEach((link) => {
    const anchor = document.createElement('a');
    anchor.className = `chart-link ${link.kind === 'viewer' ? 'secondary' : ''}`.trim();
    anchor.href = link.href;
    anchor.target = '_blank';
    anchor.rel = 'noopener noreferrer';
    anchor.textContent = link.label || link.href;
    links.appendChild(anchor);
  });

  article.appendChild(links);
  return article;
}

async function loadManifest() {
  const response = await fetch(manifestPath, { cache: 'no-store' });

  if (!response.ok) {
    throw new Error(`Could not load ${manifestPath} (${response.status})`);
  }

  return response.json();
}

async function init() {
  try {
    const manifest = await loadManifest();
    const samples = manifest.samples || [];

    if (samples.length === 0) {
      statusNode.textContent = 'No chart folders found.';
      renderEmpty('No samples are available yet.');
      return;
    }

    statusNode.textContent = `Loaded ${samples.length} sample${samples.length === 1 ? '' : 's'}.`;
    chartGrid.innerHTML = '';
    samples.forEach((sample) => {
      chartGrid.appendChild(renderSample(sample));
    });
  } catch (error) {
    statusNode.textContent = 'Unable to load the chart manifest.';
    renderEmpty(`Unable to load the chart manifest: ${error.message}`, 'error-state');
  }
}

init();
