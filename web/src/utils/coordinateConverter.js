/**
 * Convert Decimal Degrees to Degrees Minutes Seconds (DMS)
 * @param {number} decimal - Decimal degrees
 * @param {boolean} isLatitude - True for latitude, false for longitude
 * @returns {Object} {degrees, minutes, seconds, direction}
 */
export const decimalToDMS = (decimal, isLatitude = true) => {
  if (isNaN(decimal) || decimal === null || decimal === undefined) {
    return { degrees: '', minutes: '', seconds: '', direction: isLatitude ? 'N' : 'E' };
  }

  const absDecimal = Math.abs(decimal);
  const degrees = Math.floor(absDecimal);
  const minutesFloat = (absDecimal - degrees) * 60;
  const minutes = Math.floor(minutesFloat);
  const seconds = (minutesFloat - minutes) * 60;

  let direction;
  if (isLatitude) {
    direction = decimal >= 0 ? 'N' : 'S';
  } else {
    direction = decimal >= 0 ? 'E' : 'W';
  }

  return {
    degrees: degrees.toString(),
    minutes: minutes.toString(),
    seconds: seconds.toFixed(1),
    direction: direction
  };
};

/**
 * Convert Degrees Minutes Seconds (DMS) to Decimal Degrees
 * @param {number} degrees - Degrees
 * @param {number} minutes - Minutes
 * @param {number} seconds - Seconds
 * @param {string} direction - N, S, E, or W
 * @returns {number} Decimal degrees
 */
export const dmsToDecimal = (degrees, minutes, seconds, direction) => {
  const deg = parseFloat(degrees) || 0;
  const min = parseFloat(minutes) || 0;
  const sec = parseFloat(seconds) || 0;

  let decimal = deg + (min / 60) + (sec / 3600);

  if (direction === 'S' || direction === 'W') {
    decimal = -decimal;
  }

  return decimal;
};

/**
 * Parse DMS string format like "12°58'05.5"N" or "79°09'21.3"E"
 * @param {string} dmsString - DMS format string
 * @returns {Object|null} {degrees, minutes, seconds, direction} or null if invalid
 */
export const parseDMSString = (dmsString) => {
  if (!dmsString || typeof dmsString !== 'string') {
    return null;
  }

  // Match patterns like: 12°58'05.5"N or 12°58'05.5" N or 12 58 05.5 N
  const patterns = [
    /(\d+)°\s*(\d+)['′]\s*([\d.]+)["″]?\s*([NSEW])/i,  // 12°58'05.5"N
    /(\d+)\s+(\d+)\s+([\d.]+)\s*([NSEW])/i,              // 12 58 05.5 N
    /(\d+)°\s*(\d+)['′]\s*([\d.]+)["″]?\s*([NSEW])/i,   // 12° 58' 05.5" N
  ];

  for (const pattern of patterns) {
    const match = dmsString.trim().match(pattern);
    if (match) {
      return {
        degrees: match[1],
        minutes: match[2],
        seconds: match[3],
        direction: match[4].toUpperCase()
      };
    }
  }

  return null;
};

/**
 * Format DMS object to string like "12°58'05.5"N"
 * @param {Object} dms - {degrees, minutes, seconds, direction}
 * @returns {string} Formatted DMS string
 */
export const formatDMSString = (dms) => {
  if (!dms || !dms.degrees) return '';
  return `${dms.degrees}°${dms.minutes}'${dms.seconds}"${dms.direction}`;
};





