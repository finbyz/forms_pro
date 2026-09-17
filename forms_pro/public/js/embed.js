(function() {
    window.FormsPro = {
        init: function(config) {
            const { formUrl, containerId } = config;
            const container = document.getElementById(containerId);
            if (!container) return;
            
            const iframe = document.createElement("iframe");
            iframe.src = formUrl;
            iframe.style.width = "100%";
            iframe.style.border = "none";
            iframe.style.minHeight = "400px";
            iframe.scrolling = "no";
            
            container.appendChild(iframe);
            
            window.addEventListener("message", function(event) {
                // Resize iframe when form content changes height
                if (event.data && event.data.type === "formspro:resize") {
                    if (event.data.height) {
                        iframe.style.height = event.data.height + "px";
                    }
                }
                // Handle submission callback
                if (event.data && event.data.type === "formspro:submitted") {
                    if (config.onSuccess) {
                        config.onSuccess(event.data.payload);
                    }
                }
            });
        }
    };
})();
