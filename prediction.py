# -*- coding: utf-8 -*-
import json
from flask import Flask, request
from keras.models import load_model
import pandas as pd
import numpy as np

app = Flask(__name__)

@app.route('/api/predict', methods=['POST'])
def predict_result():
    data_raw = request.json

    df = pd.read_csv('df.csv')
    for col in df.columns:
        df[col].values[:] = 0

    data = json.loads(json.dumps(data_raw))
    df_client = pd.DataFrame.from_dict([data])

    # Установка значений категориальных признаков (домашняя и гостевые команды, судья, день недели)
    home_team = df_client['homeTeam'][0]
    away_team = df_client['awayTeam'][0]
    referee = df_client['referee'][0]
    day_of_week = df_client['dayOfWeek'][0]


    home_team_column = 'HomeTeam_{0}'.format(home_team)
    away_team_column = 'AwayTeam_{0}'.format(away_team)
    referee_column = 'Referee_{0}'.format(referee)
    day_of_week_column = 'day_of_week_{0}'.format(day_of_week)

    df[home_team_column][0] = 1
    df[away_team_column][0] = 1
    df[referee_column][0] = 1
    df[day_of_week_column][0] = 1

    # Подсчет текущей формы команд в очках

    form_home = df_client['homeForm'][0]
    form_away = df_client['awayForm'][0]

    def set_form_points(row):
        counter_home_5 = 0
        counter_away_5 = 0

        counter_home_3 = 0
        counter_away_3 = 0

        # Форма за 5 матчей
        for i, c in enumerate(form_home):
            if c == 'W':
                counter_home_5 += 3
            elif c == 'D':
                counter_home_5 += 1
            else:
                counter_home_5 += 0 

        for i, c in enumerate(form_away):
            if c == 'W':
                counter_away_5 += 3
            elif c == 'D':
                counter_away_5 += 1
            else:
                counter_away_5 += 0
            
            row['form_points_home_5'] = counter_home_5
            row['form_points_away_5'] = counter_away_5
            row['form_points_diff_5'] = counter_home_5 - counter_away_5

        # Форма за 3 матча
        for i, c in enumerate(form_home[-3:]):
            if c == 'W':
                counter_home_3 += 3
            elif c == 'D':
                counter_home_3 += 1
            else:
                counter_home_3 += 0 
        
        for i, c in enumerate(form_away[-3:]):
            if c == 'W':
                counter_away_3 += 3
            elif c == 'D':
                counter_away_3 += 1
            else:
                counter_away_3 += 0

            row['form_points_home_3'] = counter_home_3
            row['form_points_away_3'] = counter_away_3
            row['form_points_diff_3'] = counter_home_3 - counter_away_3

        return row

    df = df.apply(set_form_points, axis=1)

    # Создании признаков серий побед и поражений

    def set_lose_streak_win_streak(row):
    # Серии поражений
        if form_home[-3:] == 'LLL':
            row['ls_3_home'] = 1
        else:
            row['ls_3_home'] = 0
        if form_away[-3:] == 'LLL':
            row['ls_3_away'] = 1
        else:
            row['ls_3_away'] = 0

        if form_home == 'LLLLL':
            row['ls_5_home'] = 1
        else:
            row['ls_5_home'] = 0
        if form_away == 'LLLLL':
            row['ls_5_away'] = 1
        else:
            row['ls_5_away'] = 0

        # Серии побед
        if form_home[-3:] == 'WWW':
            row['ws_3_home'] = 1
        else:
            row['ws_3_home'] = 0
        if form_away[-3:] == 'WWW':
            row['ws_3_away'] = 1
        else:
            row['ws_3_away'] = 0
        
        if form_home == 'WWWWW':
            row['ws_5_home'] = 1
        else:
            row['ws_5_home'] = 0
        if form_away == 'WWWWW':
            row['ws_5_away'] = 1
        else:
            row['ws_5_away'] = 0

        return row

    df = df.apply(set_lose_streak_win_streak, axis=1)

    for column in df_client:
        if type(df_client[column][0]) == str and len(df_client[column][0]) > 15:
            df_client[column][0] = df_client[column][0].split()
            map_object = map(int, df_client[column][0])
            df_client[column][0] = list(map_object)

    # Создание статистики с усредненными значениями для каждой команды в конкретный момент
    def set_team_stats_numbers(row):
        # Среднее забитых и пропущенных голов за последние 10, 5, 3 матча
        row['home_goals_scored_last_10_matches'] = sum(df_client['goalsScoredHome'][0])/10
        row['home_goals_conceded_last_10_matches'] = sum(df_client['goalsConcededHome'][0])/10
        row['away_goals_scored_last_10_matches'] = sum(df_client['goalsScoredAway'][0])/10
        row['away_goals_conceded_last_10_matches'] = sum(df_client['goalsConcededAway'][0])/10

        row['home_goals_scored_last_5_matches'] = sum(df_client['goalsScoredHome'][0][-5:])/5
        row['home_goals_conceded_last_5_matches'] = sum(df_client['goalsConcededHome'][0][-5:])/5
        row['away_goals_scored_last_5_matches'] = sum(df_client['goalsScoredAway'][0][-5:])/5
        row['away_goals_conceded_last_5_matches'] = sum(df_client['goalsConcededAway'][0][-5:])/5

        row['home_goals_scored_last_3_matches'] = sum(df_client['goalsScoredHome'][0][-3:])/3
        row['home_goals_conceded_last_3_matches'] = sum(df_client['goalsConcededHome'][0][-3:])/3
        row['away_goals_scored_last_3_matches'] = sum(df_client['goalsScoredAway'][0][-3:])/3
        row['away_goals_conceded_last_3_matches'] = sum(df_client['goalsConcededAway'][0][-3:])/3


        # Среднее забитых и пропущенных голов в 1 тайме за последние 10, 5, 3 матча
        row['home_goals_scored_last_10_matches_1time'] = sum(df_client['goalsScoredHome1time'][0])/10
        row['home_goals_conceded_last_10_matches_1time'] = sum(df_client['goalsConcededHome1time'][0])/10
        row['away_goals_scored_last_10_matches_1time'] = sum(df_client['goalsScoredAway1time'][0])/10
        row['away_goals_conceded_last_10_matches_1time'] = sum(df_client['goalsConcededAway1time'][0])/10

        row['home_goals_scored_last_5_matches_1time'] = sum(df_client['goalsScoredHome1time'][0][-5:])/5
        row['home_goals_conceded_last_5_matches_1time'] = sum(df_client['goalsConcededHome1time'][0][-5:])/5
        row['away_goals_scored_last_5_matches_1time'] = sum(df_client['goalsScoredAway1time'][0][-5:])/5
        row['away_goals_conceded_last_5_matches_1time'] = sum(df_client['goalsConcededAway1time'][0][-5:])/5

        row['home_goals_scored_last_3_matches_1time'] = sum(df_client['goalsScoredHome1time'][0][-3:])/3
        row['home_goals_conceded_last_3_matches_1time'] = sum(df_client['goalsConcededHome1time'][0][-3:])/3
        row['away_goals_scored_last_3_matches_1time'] = sum(df_client['goalsScoredAway1time'][0][-3:])/3
        row['away_goals_conceded_last_3_matches_1time'] = sum(df_client['goalsConcededAway1time'][0][-3:])/3


        # Среднее выполненных и допущенных ударов за последние 10, 5, 3 матча
        row['home_shots_made_last_10_matches'] = sum(df_client['shotsMadeHome'][0])/10
        row['home_shots_allowed_last_10_matches'] = sum(df_client['shotsAllowedHome'][0])/10
        row['away_shots_made_last_10_matches'] = sum(df_client['shotsMadeAway'][0])/10
        row['away_shots_allowed_last_10_matches'] = sum(df_client['shotsAllowedAway'][0])/10

        row['home_shots_made_last_5_matches'] = sum(df_client['shotsMadeHome'][0][-5:])/5
        row['home_shots_allowed_last_5_matches'] = sum(df_client['shotsAllowedHome'][0][-5:])/5
        row['away_shots_made_last_5_matches'] = sum(df_client['shotsMadeAway'][0])/5
        row['away_shots_allowed_last_5_matches'] = sum(df_client['shotsAllowedAway'][0][-5:])/5

        row['home_shots_made_last_3_matches'] = sum(df_client['shotsMadeHome'][0][-3:])/3
        row['home_shots_allowed_last_3_matches'] = sum(df_client['shotsAllowedHome'][0][-3:])/3
        row['away_shots_made_last_3_matches'] = sum(df_client['shotsMadeAway'][0][-3:])/3
        row['away_shots_allowed_last_3_matches'] = sum(df_client['shotsAllowedAway'][0][-3:])/3


        # Среднее выполненных и допущенных ударов в створ ворот за последние 10, 5, 3 матча
        row['home_shots_target_made_last_10_matches'] = sum(df_client['shotsTargetMadeHome'][0])/10
        row['home_shots_target_allowed_last_10_matches'] = sum(df_client['shotsTargetAllowedHome'][0])/10
        row['away_shots_target_made_last_10_matches'] = sum(df_client['shotsTargetMadeAway'][0])/10
        row['away_shots_target_allowed_last_10_matches'] = sum(df_client['shotsAllowedAway'][0])/10

        row['home_shots_target_made_last_5_matches'] = sum(df_client['shotsTargetMadeHome'][0][-5:])/5
        row['home_shots_target_allowed_last_5_matches'] = sum(df_client['shotsTargetAllowedHome'][0][-5:])/5
        row['away_shots_target_made_last_5_matches'] = sum(df_client['shotsTargetMadeAway'][0])/5
        row['away_shots_target_allowed_last_5_matches'] = sum(df_client['shotsTargetAllowedAway'][0][-5:])/5

        row['home_shots_target_made_last_3_matches'] = sum(df_client['shotsTargetMadeHome'][0][-3:])/3
        row['home_shots_target_allowed_last_3_matches'] = sum(df_client['shotsTargetAllowedHome'][0][-3:])/3
        row['away_shots_target_made_last_3_matches'] = sum(df_client['shotsTargetMadeAway'][0][-3:])/3
        row['away_shots_target_allowed_last_3_matches'] = sum(df_client['shotsTargetAllowedAway'][0][-3:])/3
        

        # Среднее выполненных и допущенных угловых за последние 10, 5, 3 матча
        row['home_corners_made_last_10_matches'] = sum(df_client['cornersMadeHome'][0])/10
        row['home_corners_allowed_last_10_matches'] = sum(df_client['cornersAllowedHome'][0])/10
        row['away_corners_made_last_10_matches'] = sum(df_client['cornersMadeAway'][0])/10
        row['away_corners_allowed_last_10_matches'] = sum(df_client['cornersAllowedAway'][0])/10

        row['home_corners_made_last_5_matches'] = sum(df_client['cornersMadeHome'][0][-5:])/5
        row['home_corners_allowed_last_5_matches'] = sum(df_client['cornersAllowedHome'][0][-5:])/5
        row['away_corners_made_last_5_matches'] = sum(df_client['cornersMadeAway'][0])/5
        row['away_corners_allowed_last_5_matches'] = sum(df_client['cornersAllowedAway'][0][-3:])/3

        row['home_corners_made_last_3_matches'] = sum(df_client['cornersMadeHome'][0][-3:])/3
        row['home_corners_allowed_last_3_matches'] = sum(df_client['cornersAllowedHome'][0][-3:])/3
        row['away_corners_made_last_3_matches'] = sum(df_client['cornersMadeAway'][0][-3:])/3
        row['away_corners_allowed_last_3_matches'] = sum(df_client['cornersAllowedAway'][0][-3:])/3

        # Среднее выполненных и допущенных нарушений правил за последние 10, 5, 3 матча
        row['home_fouls_made_last_10_matches'] = sum(df_client['foulsMadeHome'][0])/10
        row['home_fouls_allowed_last_10_matches'] = sum(df_client['foulsAllowedHome'][0])/10
        row['away_fouls_made_last_10_matches'] = sum(df_client['foulsMadeAway'][0])/10
        row['away_fouls_allowed_last_10_matches'] = sum(df_client['foulsAllowedAway'][0])/10

        row['home_fouls_made_last_5_matches'] = sum(df_client['foulsMadeHome'][0][-5:])/5
        row['home_fouls_allowed_last_5_matches'] = sum(df_client['foulsAllowedHome'][0][-5:])/5
        row['away_fouls_made_last_5_matches'] = sum(df_client['foulsMadeAway'][0])/5
        row['away_fouls_allowed_last_5_matches'] = sum(df_client['foulsAllowedAway'][0][-3:])/3

        row['home_fouls_made_last_3_matches'] = sum(df_client['foulsMadeHome'][0][-3:])/3
        row['home_fouls_allowed_last_3_matches'] = sum(df_client['foulsAllowedHome'][0][-3:])/3
        row['away_fouls_made_last_3_matches'] = sum(df_client['foulsMadeAway'][0][-3:])/3
        row['away_fouls_allowed_last_3_matches'] = sum(df_client['foulsAllowedAway'][0][-3:])/3

        # Среднее количество желтых и красных карточек за последние 10 матчей
        row['home_yellow_cards_last_10_matches'] = sum(df_client['yellowCardsHome'][0])/10
        row['home_red_cards_last_10_matches'] = sum(df_client['redCardsHome'][0])/10
        row['away_yellow_cards_last_10_matches'] = sum(df_client['yellowCardsAway'][0])/10
        row['away_red_cards_last_10_matches'] = sum(df_client['redCardsAway'][0])/10

        return row

    df = df.apply(set_team_stats_numbers, axis=1)

    predict = model.predict(df.head(1))
    classes_x = np.argmax(predict,axis=1)
    print(predict)
    print(classes_x)
    

    return { "prediction": pd.Series(classes_x).to_json(orient='values'), "probabilities": pd.Series(predict[0]).to_json(orient='values') }

if __name__ == '__main__':
    model = load_model('.')
    app.run()