import os

class AceStepHandler:
    def initialize_service(self, project_root, config_path, device, offload_to_cpu=False,
                           quantization=None):
        # Deliberately has no `use_flash_attention` parameter, to exercise kwarg filtering.
        self.config_path = config_path
        log = os.environ.get("FAKE_INIT_LOG")
        if log:  # lets tests count model loads across jobs
            with open(log, "a") as f:
                f.write(f"{config_path} offload={offload_to_cpu}\n")
        return ("ready", True)
