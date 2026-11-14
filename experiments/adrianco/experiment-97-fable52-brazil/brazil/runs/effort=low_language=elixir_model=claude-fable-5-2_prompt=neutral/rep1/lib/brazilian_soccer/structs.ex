defmodule BrazilianSoccer.Match do
  @moduledoc "A played match, possibly merged from several source files."
  defstruct [
    :id,
    :date,
    :time,
    :season,
    :competition,
    :round,
    :stage,
    :home,
    :away,
    :home_name,
    :away_name,
    :home_goals,
    :away_goals,
    :arena,
    stats: %{},
    sources: []
  ]
end

defmodule BrazilianSoccer.Player do
  @moduledoc "A player from the FIFA dataset."
  defstruct [
    :id,
    :name,
    :age,
    :nationality,
    :overall,
    :potential,
    :club,
    :club_key,
    :position,
    :jersey,
    :height,
    :weight,
    :foot,
    :value,
    :wage,
    attributes: %{}
  ]
end
