// OutputCanvas Custom Element for Chainlit
class OutputCanvas extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
    }
    
    connectedCallback() {
        this.render();
    }
    
    render() {
        const props = this.getAttribute('props') ? JSON.parse(this.getAttribute('props')) : {};
        
        this.shadowRoot.innerHTML = `
            <style>
                :host {
                    display: block;
                    width: 100%;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                }
                
                .canvas-container {
                    background: white;
                    border-radius: 12px;
                    padding: 24px;
                    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
                    border: 1px solid #e1e5e9;
                }
                
                .canvas-header {
                    border-bottom: 2px solid #e1e5e9;
                    padding-bottom: 16px;
                    margin-bottom: 24px;
                }
                
                .canvas-title {
                    font-size: 24px;
                    font-weight: 700;
                    color: #2c3e50;
                    margin: 0 0 8px 0;
                }
                
                .canvas-timestamp {
                    color: #7f8c8d;
                    font-size: 14px;
                }
                
                .canvas-content {
                    line-height: 1.6;
                    color: #34495e;
                }
                
                .agent-info {
                    background: #f8f9fa;
                    border-left: 4px solid #3498db;
                    padding: 16px;
                    margin: 16px 0;
                    border-radius: 4px;
                }
                
                .output-section {
                    background: #f1f3f4;
                    border-radius: 8px;
                    padding: 20px;
                    margin: 20px 0;
                    border: 1px solid #e0e0e0;
                }
                
                .output-title {
                    font-weight: 600;
                    color: #2c3e50;
                    margin-bottom: 12px;
                    font-size: 18px;
                }
                
                .content-text {
                    white-space: pre-wrap;
                    word-wrap: break-word;
                }
                
                .status-badge {
                    display: inline-block;
                    background: #27ae60;
                    color: white;
                    padding: 4px 12px;
                    border-radius: 20px;
                    font-size: 12px;
                    font-weight: 600;
                    margin-left: 8px;
                }
            </style>
            
            <div class="canvas-container">
                <div class="canvas-header">
                    <h2 class="canvas-title">${props.title || 'Output Canvas'}</h2>
                    <div class="canvas-timestamp">${props.timestamp ? new Date(props.timestamp).toLocaleString() : ''}</div>
                </div>
                
                <div class="canvas-content">
                    ${this.formatContent(props.content || '')}
                </div>
            </div>
        `;
    }
    
    formatContent(content) {
        if (!content) return '<p>No content available</p>';
        
        // If content is a string, try to parse it
        if (typeof content === 'string') {
            try {
                const parsed = JSON.parse(content);
                return this.formatObjectContent(parsed);
            } catch (e) {
                // Handle markdown-style content
                const formattedContent = content.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
                return `<div class="content-text">${formattedContent}</div>`;
            }
        }
        
        return this.formatObjectContent(content);
    }
    
    formatObjectContent(obj) {
        let html = '';
        
        // Handle different object structures
        if (obj.Agent) {
            html += `<div class="agent-info">
                <strong>Agent:</strong> ${obj.Agent}
            </div>`;
        }
        
        if (obj.Section) {
            html += `<div class="agent-info">
                <strong>Section:</strong> ${obj.Section}
            </div>`;
        }
        
        if (obj.Summary) {
            html += `<div class="agent-info">
                <strong>Summary:</strong> ${obj.Summary}
            </div>`;
        }
        
        if (obj['Generated Output']) {
            html += `<div class="output-section">
                <div class="output-title">Generated Output</div>
                <div class="content-text">${obj['Generated Output']}</div>
            </div>`;
        }
        
        // Handle direct content without object structure
        if (!html && typeof obj === 'string') {
            html = `<div class="content-text">${obj}</div>`;
        }
        
        return html || '<p>Content formatted successfully</p>';
    }
    
    static get observedAttributes() {
        return ['props'];
    }
    
    attributeChangedCallback(name, oldValue, newValue) {
        if (name === 'props' && oldValue !== newValue) {
            this.render();
        }
    }
}

// Register the custom element
customElements.define('output-canvas', OutputCanvas);
