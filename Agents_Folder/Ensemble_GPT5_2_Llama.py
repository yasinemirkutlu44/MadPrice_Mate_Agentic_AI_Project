from Agents_Folder.Agent_Colours import Agent
from Agents_Folder.Fine_Tuned_Lllama import SpecialistAgent
from Agents_Folder.GPT_5_2_agent import FrontierAgent
from Agents_Folder.preprocessor import Preprocessor


class EnsembleAgent(Agent):
    name = "Ensemble Agent"
    color = Agent.YELLOW

    def __init__(self, collection):
        """
        Create an instance of Ensemble, by creating each of the models
        And loading the weights of the Ensemble
        """
        self.log("Initializing Ensemble Agent")
        self.specialist = SpecialistAgent() # First model: Fine-tuned Llama 3.2
        self.frontier = FrontierAgent(collection) # Second model: GPT-5.2
        self.preprocessor = Preprocessor()
        self.log("Ensemble Agent is ready")

    def price(self, description: str) -> float:
        """
        Run this ensemble model
        Ask each of the models to price the product
        Then use the Linear Regression model to return the weighted price
        :param description: the description of a product
        :return: an estimate of its price
        """
        self.log("Running Ensemble Agent - preprocessing text")
        rewrite = self.preprocessor.preprocess(description)
        self.log(f"Pre-processed text using {self.preprocessor.model_name}")
        specialist = self.specialist.price(rewrite)
        frontier = self.frontier.price(rewrite)
        combined = frontier * 0.9 + specialist * 0.1
        self.log(f"Ensemble Agent complete - returning ${combined:.2f}")
        return combined
