;;; Load the verified CadBridge once per ZWCAD process, across drawing tabs.
;;; Remove this file from APPLOAD / Startup Suite to disable autoload.
(vl-load-com)
(defun cadbridge:startup (/ dll result)
  (setq dll "C:/Users/luerh/.codex/skills/zwcad-control/assets/zwcad2025/CadBridge-Compat.Dev64.dll")
  (cond
    ((or (vl-bb-ref 'cadbridge-dev64-startup-attempted) (vl-bb-ref 'cadbridge-dev62-startup-attempted))
      (princ "\nCadBridge startup: already handled in this CAD session."))
    ((not (findfile dll))
      (princ (strcat "\nCadBridge startup: DLL not found: " dll)))
    (t
      ;; Mark the attempt before NETLOAD, preventing repeated prompts per drawing.
      ;; A canceled security prompt is not evidence of a successful load.
      (vl-bb-set 'cadbridge-dev64-startup-attempted T)
      (setq result (vl-catch-all-apply 'command (list "_.NETLOAD" dll)))
      (if (vl-catch-all-error-p result)
        (princ (strcat "\nCadBridge startup error: " (vl-catch-all-error-message result)))
        (princ "\nCadBridge startup: load requested; API ready confirms success.")))))
(cadbridge:startup)
(princ)
