function testJS() {
    const resultElement = document.getElementById('result');
    resultElement.textContent = '🎉 JavaScript is working! Your server correctly serves JS files.';
    resultElement.style.animation = 'fadeIn 0.5s';
}

// Add some CSS animation via JavaScript
const style = document.createElement('style');
style.textContent = `
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(-10px); }
        to { opacity: 1; transform: translateY(0); }
    }
`;
document.head.appendChild(style);

console.log('HTTP Server Test - JavaScript loaded successfully!');
