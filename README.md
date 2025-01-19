# raman_dft

primeiro, baixa o conda https://anaconda.org/anaconda/conda
dps instala 
dps q tiver instalado, vai no diretorio desse repositorio aq pelo explorador de arquivo do windows, clica c o botao dirieto na tela, e clica em abrir terminal 
no terminal, digita "conda env create -f environment.yml", aperta enter, dps digita "conda activate orcaenv" 

vai pro site oficial do orca https://orcaforum.kofo.mpg.de 
cria uma conta, vai pra area de downloads clica em orca 6.0.0 e baixa o instalador p windows x86

qnd baixar abre o instalador, instala 
e dps segue oq esse tutorial fala aq p colocar a variavel de ambiente https://www.faccts.de/docs/orca/5.0/tutorials/first_steps/install.html

dps disso, abre no vscode o arquivo raman_wrapper q ta dentro de scripts, ai eh so rodar ele q vai gerar o plot(demora um pouco p rodar)
se quiser colocar mais geometria, so colocar o arquivo .xyz na pasta geometries, no msm formato q ta o butano la
p mudar os parametros tipo temperatura e comprimento de onda do laser, eh so mudar oq ta escrito na chamada da funcao main no final do arquivo
