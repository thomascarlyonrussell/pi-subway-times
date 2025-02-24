function visualizeBitmap(bitmapText) {
    const lines = bitmapText.split('\n');
    const bbxLine = lines.find(line => line.startsWith('BBX'));
    const bbxWidth = parseInt(bbxLine.split(' ')[1], 10);
    const bitmapLines = lines.slice(lines.indexOf('BITMAP') + 1, lines.indexOf('ENDCHAR'));
    const binaryStrings = bitmapLines.map(line => {
        const binaryString = parseInt(line, 16).toString(2).padStart(bbxWidth, '0');
        return binaryString.padEnd(bbxWidth, '0');
    });
    const matrix = binaryStrings.map(binaryString => binaryString.split('').map(bit => bit === '1' ? '●' : '○'));
    const visualization = matrix.map(row => row.join(' ')).join('<br>');
    document.getElementById('bitmap-visualization').innerHTML = visualization;
}

// Example usage:
const exampleBitmap = `
STARTCHAR G
ENCODING 70
SWIDTH 611 0
DWIDTH 5 0
BBX 12 9 0 0
BITMAP
3E0
7F0
E38
EF8
E78
EF8
EF8
7F0
3E0
ENDCHAR
`;
visualizeBitmap(exampleBitmap);
