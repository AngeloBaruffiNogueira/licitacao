import requests
import pandas as pd
from typing import Dict, Any, Optional, List
from tqdm import tqdm

BASE_URL = "https://pncp.gov.br/api/consulta"
ENDPOINT = "/v1/contratacoes/proposta"
PAGE_SIZE = 50  # Fetch items per page to reduce the number of requests

def query_all_contracts(params: Dict[str, Any]) -> Optional[pd.DataFrame]:
    """
    Queries all pages of contracts from the API for the given parameters
    and returns the data in a single pandas DataFrame.

    Args:
        params (dict): Dictionary with the request parameters.

    Returns:
        A single DataFrame with all contract data, or None in case of an error.
    """
    url = f"{BASE_URL}{ENDPOINT}"
    all_data: List[pd.DataFrame] = []
    page = 1
    total_pages = None
    pbar = None

    print("Starting data fetch from API...")
    while True:
        query_params = params.copy()
        query_params["pagina"] = page
        query_params["tamanhoPagina"] = PAGE_SIZE

        try:
            df, paginasRestantes, totalPaginas = _fetch_page(url, query_params)
            if df is None:  # Error occurred
                return None
         
            if total_pages is None:
                total_pages = totalPaginas
                pbar = tqdm(total=total_pages, desc="Fetching pages")
            if pbar:
                pbar.update(1)

            print(f"Fetched page {page}/{totalPaginas} with {len(df)} results.")
            all_data.append(df)
            if paginasRestantes == 0:  # No more data
                print("All pages fetched.")
                break
            page += 1

        except Exception as e:
            print(f"An unexpected error occurred during pagination: {e}")
            return None

    if pbar:
        pbar.close()

    if not all_data:
        return pd.DataFrame()  # Return empty DataFrame if no data found

    return pd.concat(all_data, ignore_index=True)


def _fetch_page(url: str, params: Dict[str, Any]) -> Optional[pd.DataFrame]:
    """Fetches a single page of data from the API."""

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()  # Raises an exception for error status (4xx or 5xx)
        data = response.json()

        if "data" in data:
            return pd.DataFrame(data["data"]), data["paginasRestantes"], data["totalPaginas"]
        else:
            print("Error: API response does not contain valid data.")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Error during request: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None


def save_to_csv(df: pd.DataFrame, filename: str = "contracts.csv"):
    """Saves the data from a DataFrame to a CSV file.

    Args:
        df (pandas.DataFrame): DataFrame with the data.
        filename (str): Name of the CSV file to be created.
    """
    if df is not None and not df.empty:
        df.to_csv(filename, index=False)
        print(f"Data saved to: {filename}")
    else:
        print("No data to save.")


def save_to_pickle(df: pd.DataFrame, filename: str = "contracts.pkl"):
    """Saves the data from a DataFrame to a pickle file.

    Args:
        df (pandas.DataFrame): DataFrame with the data.
        filename (str): Name of the pickle file to be created.
    """
    if df is not None and not df.empty:
        df.to_pickle(filename)
        print(f"Data saved to: {filename}")
    else:
        print("No data to save.")


def process_data(df: pd.DataFrame) -> pd.DataFrame:
    """Process the dataframe to a cleaner version
    Args:
        df (pandas.DataFrame): DataFrame with the data.

    """
    #remove duplicates keeping unique using as key the columns valorTotalHomologado and objetoCompra
    df.drop_duplicates(subset=['valorTotalHomologado', 'objetoCompra'], inplace=True)

    #ensure that datetime on the date using format as 2027-06-18T17:30:00
    df['dataAberturaProposta'] = pd.to_datetime(df['dataAberturaProposta'], errors='coerce')
    df['dataEncerramentoProposta'] = pd.to_datetime(df['dataEncerramentoProposta'], errors='coerce')
    df['dataInclusao'] = pd.to_datetime(df['dataInclusao'], errors='coerce')
    df['dataPublicacaoPncp'] = pd.to_datetime(df['dataPublicacaoPncp'], errors='coerce')
    df['dataAtualizacao'] = pd.to_datetime(df['dataAtualizacao'], errors='coerce')
    df['dataAtualizacaoGlobal'] = pd.to_datetime(df['dataAtualizacaoGlobal'], errors='coerce')

    #copy the column valorTotalHomologado to field named valor
    df['valor'] = df['valorTotalEstimado']

    #unparse the json column orgaoEntidade into new columns
    orgao_entidade_df = pd.json_normalize(df['orgaoEntidade'])
    df = pd.concat([df.drop('orgaoEntidade', axis=1), orgao_entidade_df], axis=1)

    #inside the json file, process the poderId to with a enum conversation E:Estadual, M:Municipal,N:Nacional
    poder_map = {
        'E': 'Estadual',
        'M': 'Municipal',
        'N': 'Nacional'
    }
    df['poder'] = df['poderId'].map(poder_map)

    # Unparse 'unidadeOrgao' JSON column
    unidade_orgao_df = pd.json_normalize(df['unidadeOrgao'])
    df = pd.concat([df.drop('unidadeOrgao', axis=1), unidade_orgao_df], axis=1)

    return df




def main():
    """Main function to execute the script."""

    full_load = False

    parameters = {
        # "dataInicial": "20250618",  # Replace with the desired start date
        "dataFinal": "20400618",    # Replace with the desired end date
        # "codigoModalidadeContratacao": 6, # Replace with the desired code
        # "uf": "SC",  # Replace with the desired state code
    }

    if full_load:
        # Calls the function to query and get the data
        contracts_data = query_all_contracts(parameters)
        save_to_csv(contracts_data, "contracts.csv")
        save_to_pickle(contracts_data, 'contracts.pkl')
    else:
        #load from the pickle file
        contracts_data = pd.read_pickle("contracts.pkl")

    # Save the data to a CSV file
    if contracts_data is not None:
        contracts_data = process_data(contracts_data)
        save_to_csv(contracts_data, "contracts_clean.csv")
        save_to_pickle(contracts_data, 'contracts_clean.pkl')
        print(f"\nTotal contracts fetched: {len(contracts_data)}")
        print("\nFirst 5 rows of the combined data:")
        print(contracts_data.head())

if __name__ == "__main__":
    main()
