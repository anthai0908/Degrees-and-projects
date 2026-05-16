import os
from typing import Any, Dict, List, Optional, Union, Annotated
from langgraph.prebuilt import InjectedState

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from models.state import JobApplicationGraphState
from action import Action
import json

class AutoTool:
    def __init__(self, timeout_sec: int = 10):
        self.driver = webdriver.Firefox()
        self.timeout_sec = timeout_sec
        
    def get_general_compact_observation_all(driver, timeout=8):
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") in ("interactive", "complete")
        )
    
        js = """
            const doc = document.cloneNode(true);

            // remove obvious noise
            doc.querySelectorAll(
              "script,style,noscript,svg,canvas,iframe,.ads,.advert,.cookie,.newsletter,.social-share"
            ).forEach(n => n.remove());

            // remove tiny/empty decorative nodes
            doc.querySelectorAll("*").forEach(el => {
              const text = (el.innerText || "").trim();
              const hasInteractive = el.querySelector("a,button,input,select,textarea");
              if (!hasInteractive && text.length === 0) el.remove();
            });

            // keep full meaningful text
            return (doc.body?.innerText || "").replace(/\n{3,}/g, "\n\n").trim();
        """
        return driver.driver.execute_script(js)
    

    def _to_action(self, action: Union[Action, Dict[str, Any]]) -> Action:
        if isinstance(action, Action):
            return action
        return Action(**action)

    def take_action(
        self,
        action_list: Optional[List[Union[Action, Dict[str, Any]]]],
        step_name: Optional[str] = None,
        attempt_count: int = 1,
       
    ) -> Dict[str, Any]:
        normalized_actions: List[Action] = []
        if action_list:
            normalized_actions = [self._to_action(a) for a in action_list]

        summary: Dict[str, Any] = {
            "step_name": step_name,
            "status": "pending",
            "actions": [
                {
                    "action_type": action.action_type,
                    "target": action.target,
                    "value": action.value,
                    "status": "pending",
                }
                for action in normalized_actions
            ],
            "last_error": None,
        }

        if not normalized_actions:
            summary["status"] = "completed"
            return summary

        summary["status"] = "in_progress"

        for idx, action in enumerate(normalized_actions):
            try:
                if action.action_type == "goto":
                    self.driver.get(action.target)
                    WebDriverWait(self.driver, self.timeout_sec).until(
                        lambda d: d.execute_script("return document.readyState") == "complete"
                    )
                elif action.action_type == "click":
                    element = WebDriverWait(self.driver, self.timeout_sec).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, action.target))
                    )
                    element.click()
                    WebDriverWait(self.driver, self.timeout_sec).until(
                        lambda d: d.execute_script("return document.readyState") in ("interactive", "complete")
                    )
                elif action.action_type == "input":
                    if action.value is None:
                        raise ValueError("input action requires non-null value")
                    element = WebDriverWait(self.driver, self.timeout_sec).until(
                        EC.visibility_of_element_located((By.CSS_SELECTOR, action.target))
                    )
                    element.clear()
                    element.send_keys(action.value)
                elif action.action_type == "upload":
                    if action.value is None:
                        raise ValueError("upload action requires non-null value")
                    if not os.path.exists(action.value):
                        raise FileNotFoundError(f"upload file not found: {action.value}")
                    element = WebDriverWait(self.driver, self.timeout_sec).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, action.target))
                    )
                    element.send_keys(action.value)
                elif action.action_type == "switch_to_tab":
                    if action.value >= len(self.driver.window_handles):
                        raise ValueError("invalid tab index, must be less than number of tabs")
                    self.driver.switch_to.window(self.driver.window_handles[action.value])
                elif action.action_type ==  "extract":
                    extracted_observation = self.get_general_compact_observation_all(self.driver)
                    with open("extracted_observation.jsonl", "a", encoding="utf-8") as f:
                        f.write(extracted_observation + "\n")
                else:
                    raise ValueError(f"Unsupported action_type: {action.action_type}")
                summary["actions"][idx]["status"] = "completed"
            except Exception as e:
                summary["actions"][idx]["status"] = "failed"
                summary["status"] = "failed"
                summary["last_error"] = str(e)
                for rest_idx in range(idx + 1, len(summary["actions"])):
                    summary["actions"][rest_idx]["status"] = "skipped"
                break

        if summary["status"] != "failed":
            summary["status"] = "completed"

        return summary
