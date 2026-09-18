(function() {
    function init() {
        var elements = document.querySelectorAll("[data-forms-pro]");
        
        elements.forEach(function(el) {
            if (el.dataset.formsProLoaded) return;
            el.dataset.formsProLoaded = "true";
            
            var route = el.getAttribute("data-forms-pro");
            var domain = el.getAttribute("data-forms-pro-domain") || window.location.origin;
            
            var iframe = document.createElement("iframe");
            iframe.src = domain + "/forms/p/" + route + "?embed=1";
            iframe.style.width = "100%";
            iframe.style.border = "none";
            iframe.style.overflow = "hidden";
            iframe.scrolling = "no";
            iframe.setAttribute("title", "Forms Pro Embedded Form");
            
            el.appendChild(iframe);
            
            // Listen for postMessage from the iframe
            window.addEventListener("message", function(event) {
                // Ideally check event.origin against allowed domains
                if (event.source !== iframe.contentWindow) return;
                
                try {
                    var data = JSON.parse(event.data);
                    
                    if (data.source === "forms-pro") {
                        if (data.event === "formspro:resize" && data.height) {
                            iframe.style.height = data.height + "px";
                        } else if (data.event === "formspro:submitted") {
                            // Forward event to parent listeners
                            var customEvent = new CustomEvent("formspro:submitted", { detail: data });
                            document.dispatchEvent(customEvent);
                        }
                    }
                } catch (e) {
                    // Ignore parsing errors for non-JSON messages
                }
            });
        });
    }
    
    // Auto-init on load
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
