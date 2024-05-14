import random
from datetime import datetime
from pymongo import MongoClient
from app.db.database import Survey,SurveyQuestion,SurveyType
from app.core.config import settings
from bson import ObjectId
from datetime import datetime, timedelta

class SurveyServiceException(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class SurveyService:
    
    def startSurvey(self,surveyType, userId):

       # Check for existing surveys
        one_year_ago = datetime.now() - timedelta(days=365)
        existing_surveys = list(Survey.find({'userId': userId, 'surveyType': surveyType}))

        # Check for a completed survey within the last year
        completed_survey = next((s for s in existing_surveys if s.get('endDateTime') and s.get('endDateTime') > one_year_ago), None)
        if completed_survey:
            raise SurveyServiceException("A valid completed survey already exists for this user and type.")

        # Check for a non-completed survey
        non_completed_survey = next((s for s in existing_surveys if not s.get('endDateTime')), None)
        if non_completed_survey:
            return self.getSurveyQuestions(non_completed_survey['_id'])

        survey_type_doc = SurveyType.find_one({'surveyType': surveyType})

        if not survey_type_doc:
            raise SurveyServiceException("Survey Type Invalid.")
        
        categories = survey_type_doc['categories']
        min_score = survey_type_doc['min_score']
        max_score = survey_type_doc['max_score']

        # Selecting questions
        questions = []
        for category in categories:
            cat_questions = list(SurveyQuestion.find({'surveyType': surveyType, 'category': category}))
            questions.extend(random.sample(cat_questions, k=int(settings.SURVEY_QUESTION_COUNT / len(categories))))

        # Preparing survey document
        survey = {
            'userId': userId,
            'completionRatio': 0,
            'answers': [{'questionId': str(q['_id']), 'answer': None} for q in questions],
            'surveyType': surveyType,
            'min_score' : min_score,
            'max_score' : max_score,
            'startDateTime': datetime.now(),
            'endDateTime': None,
            'results': None
        }
        result = Survey.insert_one(survey)
        return self.getSurveyQuestions(result.inserted_id)

    def getSurveyQuestions(self,surveyId):
        survey = Survey.find_one({'_id': surveyId})

        total_questions = len(survey['answers'])
        unanswered_question_ids = [ans['questionId'] for ans in survey['answers'] if ans['answer'] is None]
        
        # Limiting the number of questions fetched to 10
        limited_unanswered_questions = unanswered_question_ids[:10]
        question_object_ids = [ObjectId(id) for id in limited_unanswered_questions]



        unanswered_questions = list(SurveyQuestion.find({'_id': {'$in': question_object_ids}}, {'content': 1}))

        answered_questions = sum(1 for ans in survey['answers'] if ans['answer'] is not None)
        unanswered_count = total_questions - answered_questions
        completion_ratio = (answered_questions / total_questions) * 100

        questions_to_return = [{'questionId': str(q['_id']), 'content': q['content']} for q in unanswered_questions]

        return {
            'surveyId' : str(surveyId),
            'answeredCount': answered_questions,
            'unansweredCount': unanswered_count,
            'completionRatio': completion_ratio,
            'questions': questions_to_return,
            'minScore' : survey['min_score'],
            'maxScore' : survey['max_score']
        }

    def collectAnswers(self, answers, surveyId , userId):
        survey = Survey.find_one({'_id': ObjectId(surveyId),'userId' : userId})
        if not survey:
            raise SurveyServiceException("No survey found for the user.")

        if not all(survey['min_score'] <= ans.answer <= survey['max_score'] for ans in answers):
            raise SurveyServiceException( "Answers must be in the range") 
        
        # Get existing answered question IDs
        existing_answer_ids = {ans['questionId'] for ans in survey['answers'] if 'answer' in ans}

        # Filter out answers that have already been given
        new_answers = [ans for ans in answers if ans.questionId not in existing_answer_ids]

        # If new_answers is empty, raise an exception
        if not new_answers:
            raise SurveyServiceException("All provided answers are for questions that have already been answered.")


        # Updating answers
        for ans in new_answers:
            Survey.update_one(
                {'_id': survey['_id'], 'answers.questionId': ans.questionId},
                {'$set': {'answers.$.answer': ans.answer}}
            )

        survey = Survey.find_one({'_id': ObjectId(surveyId),'userId' : userId})

        # Updating completion ratio
        total_questions = len(survey['answers'])
        answered_questions = sum(1 for ans in survey['answers'] if ans['answer'] is not None)
        completion_ratio = (answered_questions / total_questions) * 100
        Survey.update_one({'_id': survey['_id']}, {'$set': {'completionRatio': completion_ratio}})

        if completion_ratio < 100:
            return self.getSurveyQuestions(survey['_id'])
        else:
            survey = Survey.find_one({'_id': ObjectId(surveyId),'userId' : userId})
            self.calculate_survey_answers(survey)
            return "Survey completed!"
    
    def calculate_survey_answers(self,survey_data):
        # Initialize scores and counts for each category based on the surveyType    
        survey_type_doc = SurveyType.find_one({'surveyType': survey_data['surveyType']})
        max_score = survey_data['max_score']
        categories = survey_type_doc['categories']
        scores = {category: 0 for category in categories}
        oppositeScores = {}
        counts = {trait: 0 for trait in scores}

        question_ids = [ObjectId(ans['questionId']) for ans in survey_data['answers']]
        result = SurveyQuestion.find({'_id': {'$in': question_ids}}, {'category': 1, 'scoringType': 1})

        # Convert the result to a map
        question_list = {str(doc['_id']): {"category": doc.get('category'), "scoringType": doc.get('scoringType')} for doc in result}

        # Process each answer
        for answer_data in survey_data['answers']:
            question_id = answer_data['questionId']
            answer = answer_data['answer']
            trait = question_list.get(question_id)['category']
            scoringType = question_list.get(question_id)['scoringType']
            if trait:
                counts[trait] += 1
                if scoringType == 'HIGH':
                    scores[trait] += answer
                else:
                    scores[trait] = scores[trait] + (max_score - answer + 1) #normalizing the value on scale of max_score

        # Calculate average scores on scale of 100
        for trait in scores:
            if counts[trait] > 0:
                averageScore = scores[trait] / counts[trait]
                scores[trait] = int((averageScore / max_score) * 100)
                oppositeCategory = survey_type_doc['oppositeCategories'].get(trait);
                oppositeScores[oppositeCategory] = 100 - scores[trait]
        
        scores.update(oppositeScores)

        Survey.update_one({'_id': survey_data['_id']}, {'$set': {'results': scores}})
        ## TODO : Add opposite category for each category and return results for category and opposite category